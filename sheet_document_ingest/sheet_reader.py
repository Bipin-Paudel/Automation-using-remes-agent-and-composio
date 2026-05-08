from __future__ import annotations

import argparse
import io
import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from urllib.parse import parse_qs, urlparse

import pandas as pd
import requests

GOOGLE_SHEET_ID_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9\-_]+)")
DATE_HINT_RE = re.compile(
    r"(\b\d{1,2}(?:st|nd|rd|th)?\b.*\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\b)|"
    r"(\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\b.*\b\d{1,4}\b)|"
    r"(\b\d{1,4}[/-]\d{1,2}[/-]\d{1,4}\b)",
    re.IGNORECASE,
)
SIGN_IN_MARKERS = (
    "servicelogin",
    "sign in",
    "request access",
    "you need access",
    "accounts.google.com",
)
SHEET_SOURCE_KINDS = {"google_sheet", "csv", "excel"}
DOCUMENT_SOURCE_KINDS = {"google_doc", "text_document", "docx"}


class SheetAnalysisError(Exception):
    """Base exception for sheet and document ingestion failures."""


class SheetAccessError(SheetAnalysisError):
    """Raised when the source cannot be read because of access restrictions."""


class SheetGidError(SheetAnalysisError):
    """Raised when a Google Sheet gid is invalid or inaccessible."""


class SheetEmptyError(SheetAnalysisError):
    """Raised when the source exists but contains no readable data."""


@dataclass(slots=True)
class NormalizedSource:
    original_url: str
    fetch_url: str
    source_kind: str
    source_format: str
    spreadsheet_id: str | None = None
    document_id: str | None = None
    gid: str | None = None


@dataclass(slots=True)
class ParsedFrame:
    dataframe: pd.DataFrame
    sheet_name: str | int | None = None


def is_sheet_source_kind(source_kind: str) -> bool:
    return source_kind in SHEET_SOURCE_KINDS


def is_document_source_kind(source_kind: str) -> bool:
    return source_kind in DOCUMENT_SOURCE_KINDS


def _validate_url(url: str) -> str:
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SheetAnalysisError(
            "Invalid URL. Expected an http(s) Google Sheets, Google Docs, CSV, text, .docx, or .xlsx link."
        )
    return url.strip()


def match_sheet_source(
    url: str,
    *,
    gid: str | None = None,
) -> NormalizedSource | None:
    """Return a normalized sheet-like source when the URL matches one."""
    parsed = urlparse(url)
    hostname = parsed.netloc.lower()
    path = parsed.path.lower()
    query = parse_qs(parsed.query)

    if hostname == "docs.google.com" and "/spreadsheets/" in path:
        match = GOOGLE_SHEET_ID_RE.search(url)
        if not match:
            raise SheetAnalysisError("Invalid Google Sheets URL.")

        fragment = parse_qs(parsed.fragment)
        selected_gid = (
            str(gid).strip()
            if gid is not None
            else ((query.get("gid") or fragment.get("gid") or [None])[0])
        )
        spreadsheet_id = match.group(1)
        export_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv"
        if selected_gid:
            export_url = f"{export_url}&gid={selected_gid}"

        return NormalizedSource(
            original_url=url,
            fetch_url=export_url,
            source_kind="google_sheet",
            source_format="csv",
            spreadsheet_id=spreadsheet_id,
            gid=selected_gid,
        )

    if path.endswith(".xlsx"):
        return NormalizedSource(
            original_url=url,
            fetch_url=url,
            source_kind="excel",
            source_format="xlsx",
        )

    if path.endswith(".csv") or query.get("format") == ["csv"]:
        return NormalizedSource(
            original_url=url,
            fetch_url=url,
            source_kind="csv",
            source_format="csv",
        )

    return None


def _download_source(
    source: NormalizedSource,
    *,
    timeout_seconds: int = 30,
    max_download_bytes: int = 50 * 1024 * 1024,
) -> tuple[bytes, str, str]:
    response = None
    try:
        response = requests.get(
            source.fetch_url,
            timeout=timeout_seconds,
            stream=True,
            headers={"User-Agent": "sheet-document-ingest/1.0"},
        )
    except requests.RequestException as exc:
        raise SheetAnalysisError(f"Failed to fetch the source URL: {exc}") from exc
    try:
        if response.status_code == 400 and source.source_kind == "google_sheet" and source.gid:
            raise SheetGidError(f"Wrong sheet gid: {source.gid}")

        if response.status_code in {401, 403} and source.source_kind in {"google_sheet", "google_doc"}:
            raise SheetAccessError("Please enable 'Anyone with the link' access")

        if response.status_code >= 400:
            raise SheetAnalysisError(f"Failed to fetch the source URL: HTTP {response.status_code}")

        content = bytearray()
        for chunk in response.iter_content(chunk_size=1024 * 128):
            if not chunk:
                continue
            content.extend(chunk)
            if len(content) > max_download_bytes:
                raise SheetAnalysisError(
                    f"Dataset is too large to fetch safely ({max_download_bytes} byte limit exceeded)."
                )

        payload = bytes(content)
        content_type = (response.headers.get("content-type") or "").lower()
        response_text = payload[:8192].decode("utf-8", errors="ignore").lower()

        if source.source_kind in {"google_sheet", "google_doc"} and (
            "<html" in response_text or any(marker in response_text for marker in SIGN_IN_MARKERS)
        ):
            if any(marker in response_text for marker in SIGN_IN_MARKERS):
                raise SheetAccessError("Please enable 'Anyone with the link' access")
            if source.gid:
                raise SheetGidError(f"Wrong sheet gid: {source.gid}")
            if source.source_kind == "google_doc":
                raise SheetAnalysisError("Google Doc export failed. Verify the link and try again.")
            raise SheetAnalysisError("Google Sheet export failed. Verify the link and try again.")

        if source.source_kind in {"google_sheet", "google_doc"} and not payload:
            if source.source_kind == "google_doc":
                raise SheetEmptyError("The Google Doc export returned no data.")
            raise SheetEmptyError("The Google Sheet export returned no data.")

        return payload, content_type, str(response.url)
    finally:
        response.close()


def _parse_csv_bytes(payload: bytes, *, nrows: int | None = None) -> ParsedFrame:
    try:
        return ParsedFrame(dataframe=pd.read_csv(io.BytesIO(payload), nrows=nrows))
    except pd.errors.EmptyDataError as exc:
        raise SheetEmptyError("The sheet is empty.") from exc
    except Exception as exc:
        raise SheetAnalysisError(f"Failed to parse CSV data: {exc}") from exc


def _parse_excel_bytes(
    payload: bytes,
    *,
    sheet_name: str | int | None,
    nrows: int | None = None,
) -> ParsedFrame:
    try:
        workbook = pd.ExcelFile(io.BytesIO(payload), engine="openpyxl")
        chosen_sheet = workbook.sheet_names[0] if sheet_name is None else sheet_name
        dataframe = pd.read_excel(
            workbook,
            sheet_name=chosen_sheet,
            engine="openpyxl",
            nrows=nrows,
        )
        return ParsedFrame(dataframe=dataframe, sheet_name=chosen_sheet)
    except ValueError as exc:
        raise SheetAnalysisError(f"Invalid Excel sheet selection: {exc}") from exc
    except Exception as exc:
        raise SheetAnalysisError(f"Failed to parse Excel data: {exc}") from exc


def _detect_frame_column_type(series: pd.Series) -> str:
    non_null = series.dropna()
    if non_null.empty:
        return "empty"
    if pd.api.types.is_bool_dtype(non_null):
        return "boolean"
    if pd.api.types.is_numeric_dtype(non_null):
        return "number"
    if pd.api.types.is_datetime64_any_dtype(non_null):
        return "date"

    as_text = non_null.astype(str).str.strip()
    lowered = as_text.str.lower()
    if lowered.isin({"true", "false", "yes", "no"}).all():
        return "boolean"

    numeric_guess = pd.to_numeric(as_text, errors="coerce")
    if numeric_guess.notna().all():
        return "number"

    if _series_has_date_hints(as_text):
        date_guess = _coerce_datetime_series(as_text)
        if date_guess.notna().all():
            return "date"

    unique_ratio = non_null.nunique(dropna=True) / max(len(non_null), 1)
    if unique_ratio <= 0.5:
        return "categorical"
    return "string"


def _to_json_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if hasattr(value, "item") and callable(value.item):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _format_datetime_insight(value: pd.Timestamp) -> str:
    if (
        value.hour == 0
        and value.minute == 0
        and value.second == 0
        and value.microsecond == 0
    ):
        return value.date().isoformat()
    return value.isoformat()


def _normalize_date_text(value: str) -> str:
    compact = re.sub(r"\s+", " ", value).strip()
    normalized = re.sub(r"(?<=\d)(st|nd|rd|th)\b", "", compact, flags=re.IGNORECASE)
    has_month = bool(
        re.search(
            r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\b",
            normalized,
            re.IGNORECASE,
        )
    )
    has_year = bool(re.search(r"\b\d{4}\b", normalized))
    has_day = bool(re.search(r"\b\d{1,2}\b", normalized))
    if has_month and has_day and not has_year:
        return f"{normalized} {datetime.now().year}"
    return normalized


def _looks_like_date_text(value: str) -> bool:
    return bool(DATE_HINT_RE.search(_normalize_date_text(value)))


def _series_has_date_hints(values: pd.Series) -> bool:
    return any(_looks_like_date_text(value) for value in values.astype(str))


def _coerce_datetime_series(values: pd.Series) -> pd.Series:
    normalized = values.astype(str).map(_normalize_date_text)
    try:
        return pd.to_datetime(normalized, errors="coerce", format="mixed")
    except TypeError:
        return pd.to_datetime(normalized, errors="coerce")


def _validate_max_rows(max_rows: int | None) -> int | None:
    if max_rows is None:
        return None
    if max_rows < 0:
        raise SheetAnalysisError("max_rows must be zero or greater.")
    return max_rows


def _probe_row_limit(max_rows: int | None) -> int | None:
    if max_rows is None:
        return None
    return max_rows + 1


def _frame_to_records(df: pd.DataFrame) -> tuple[list[str], list[dict[str, Any]]]:
    clean_df = df.copy()
    clean_df.columns = [str(column) for column in clean_df.columns]
    columns = list(clean_df.columns)
    rows: list[dict[str, Any]] = []
    for _, row in clean_df.iterrows():
        rows.append({column: _to_json_value(row[column]) for column in columns})
    return columns, rows


def _build_summary(df: pd.DataFrame, *, truncated: bool) -> dict[str, Any]:
    columns = [str(column) for column in df.columns]
    return {
        "row_count": int(len(df)),
        "column_count": int(len(columns)),
        "empty_sheet": bool(df.empty or not columns),
        "truncated": truncated,
        "column_types": {
            column: _detect_frame_column_type(df[column]) for column in columns
        },
    }


def _build_insights(df: pd.DataFrame) -> dict[str, Any]:
    missing_values: dict[str, Any] = {}
    numeric_columns: dict[str, Any] = {}
    categorical_columns: dict[str, Any] = {}
    date_columns: dict[str, Any] = {}
    patterns: list[str] = []

    if df.empty:
        return {
            "missing_values": missing_values,
            "duplicate_rows": 0,
            "numeric_columns": numeric_columns,
            "categorical_columns": categorical_columns,
            "date_columns": date_columns,
            "patterns": ["The sheet has headers but no data rows."],
        }

    total_rows = max(len(df), 1)
    duplicate_rows = int(df.duplicated().sum())
    if duplicate_rows:
        patterns.append(f"Detected {duplicate_rows} duplicate row(s).")

    for column in df.columns:
        series = df[column]
        column_name = str(column)
        missing_count = int(series.isna().sum())
        if missing_count:
            missing_values[column_name] = {
                "count": missing_count,
                "ratio": round(missing_count / total_rows, 4),
            }
            if missing_count / total_rows >= 0.3:
                patterns.append(f"Column '{column_name}' has a high missing-value rate.")

        detected_type = _detect_frame_column_type(series)

        if detected_type == "number":
            numeric_series = pd.to_numeric(series, errors="coerce").dropna()
            if not numeric_series.empty:
                midpoint = max(len(numeric_series) // 2, 1)
                first_half = numeric_series.iloc[:midpoint].mean()
                second_half = numeric_series.iloc[midpoint:].mean()
                trend = "stable"
                if second_half > first_half * 1.05:
                    trend = "upward"
                elif second_half < first_half * 0.95:
                    trend = "downward"
                numeric_columns[column_name] = {
                    "min": _to_json_value(numeric_series.min()),
                    "max": _to_json_value(numeric_series.max()),
                    "mean": round(float(numeric_series.mean()), 4),
                    "trend": trend,
                }

        elif detected_type in {"categorical", "string", "boolean"}:
            top_values = (
                series.fillna("(missing)")
                .astype(str)
                .value_counts(dropna=False)
                .head(3)
            )
            categorical_columns[column_name] = [
                {"value": index, "count": int(count)}
                for index, count in top_values.items()
            ]
            if len(top_values) == 1:
                patterns.append(f"Column '{column_name}' has the same value in every row.")

        elif detected_type == "date":
            parsed_dates = _coerce_datetime_series(series).dropna()
            if not parsed_dates.empty:
                date_columns[column_name] = {
                    "min": _format_datetime_insight(parsed_dates.min()),
                    "max": _format_datetime_insight(parsed_dates.max()),
                }

    if not patterns:
        patterns.append("No strong anomalies detected in the sampled data.")

    return {
        "missing_values": missing_values,
        "duplicate_rows": duplicate_rows,
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "date_columns": date_columns,
        "patterns": patterns,
    }


def _build_result(
    source: NormalizedSource,
    parsed: ParsedFrame,
    *,
    content_type: str,
    final_url: str,
    validated_max_rows: int | None,
) -> dict[str, Any]:
    df = parsed.dataframe
    if df.empty and len(df.columns) == 0:
        raise SheetEmptyError("The sheet is empty.")

    truncated = False
    if validated_max_rows is not None and len(df) > validated_max_rows:
        df = df.head(validated_max_rows).copy()
        truncated = True

    columns, rows = _frame_to_records(df)
    return {
        "source": {
            "original_url": source.original_url,
            "fetch_url": source.fetch_url,
            "final_url": final_url,
            "source_kind": source.source_kind,
            "source_format": source.source_format,
            "spreadsheet_id": source.spreadsheet_id,
            "document_id": source.document_id,
            "gid": source.gid,
            "sheet_name": parsed.sheet_name,
            "content_type": content_type,
        },
        "columns": columns,
        "rows": rows,
        "summary": _build_summary(df, truncated=truncated),
        "insights": _build_insights(df),
    }


def analyze_sheet_source(
    source: NormalizedSource,
    *,
    sheet_name: str | int | None = None,
    max_rows: int | None = None,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """Fetch, parse, and analyze a sheet-like source."""
    validated_max_rows = _validate_max_rows(max_rows)
    payload, content_type, final_url = _download_source(
        source,
        timeout_seconds=timeout_seconds,
    )
    row_probe_limit = _probe_row_limit(validated_max_rows)

    if source.source_format == "csv" or "text/csv" in content_type:
        parsed = _parse_csv_bytes(payload, nrows=row_probe_limit)
    elif source.source_format == "xlsx":
        parsed = _parse_excel_bytes(
            payload,
            sheet_name=sheet_name,
            nrows=row_probe_limit,
        )
    else:
        raise SheetAnalysisError("Unsupported sheet response format.")

    return _build_result(
        source,
        parsed,
        content_type=content_type,
        final_url=final_url,
        validated_max_rows=validated_max_rows,
    )


def _build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze a Google Sheet, Google Doc, CSV export, text document, .docx file, or Excel file URL."
    )
    parser.add_argument("url", help="Google Sheets / Google Docs / CSV / text / DOCX / XLSX URL")
    parser.add_argument("--gid", help="Optional Google Sheets gid", default=None)
    parser.add_argument("--sheet-name", help="Optional Excel sheet name", default=None)
    parser.add_argument("--max-rows", type=int, help="Optional output row limit", default=None)
    parser.add_argument("--timeout", type=int, help="Fetch timeout in seconds", default=30)
    return parser


if __name__ == "__main__":
    from . import analyze_sheet

    cli = _build_cli()
    args = cli.parse_args()
    result = analyze_sheet(
        args.url,
        gid=args.gid,
        sheet_name=args.sheet_name,
        max_rows=args.max_rows,
        timeout_seconds=args.timeout,
    )
    print(json.dumps(result, indent=2, ensure_ascii=True))
