import asyncio
import csv
import io
import json
import re
from urllib.parse import parse_qs, urlparse

import aiohttp
from sheet_ingest.python_sheet_reader import (
    SheetAccessError,
    SheetAnalysisError,
    SheetEmptyError,
    SheetGidError,
    analyze_sheet,
    normalize_source_url,
)

GOOGLE_SHEETS_URL_RE = re.compile(
    r"https?://docs\.google\.com/spreadsheets/[^\s>]+",
    re.IGNORECASE,
)
URL_RE = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)
GOOGLE_SHEET_ID_RE = re.compile(
    r"/spreadsheets/d/([a-zA-Z0-9\-_]+)",
    re.IGNORECASE,
)
DOCUMENT_FETCH_TIMEOUT_SECONDS = 20
DOCUMENT_PREVIEW_ROW_LIMIT = 12
DOCUMENT_PREVIEW_COL_LIMIT = 12
DOCUMENT_PREVIEW_CHAR_LIMIT = 5000
DIRECT_PREVIEW_ROW_LIMIT = 3
DIRECT_PREVIEW_COL_LIMIT = 6
DIRECT_TYPE_LIMIT = 8
DIRECT_EXPORT_KEYWORDS = (
    "excel",
    "xlsx",
    "new excel file",
    "export",
    "download file",
    "create file",
    "make file",
    "give me all that data",
    "give me that data",
    "all that data",
)
DIRECT_READ_HINTS = (
    "read this",
    "read it",
    "summarize",
    "analyse",
    "analyze",
    "open this",
    "open it",
    "check this",
    "what is in",
    "what's in",
    "see this",
)
REDDIT_HINTS = (
    "reddit",
    "subreddit",
    "thread",
    "post",
    "comment",
    "where to post",
    "what to post",
)


def _extract_google_sheet_url(text: str) -> str | None:
    """Return the first Google Sheets URL found in the Slack message."""
    match = GOOGLE_SHEETS_URL_RE.search(text or "")
    if not match:
        return None
    return match.group(0).rstrip(").,]>")


def _extract_supported_document_url(text: str) -> str | None:
    """Return the first supported Google Sheet, CSV, or XLSX URL."""
    for match in URL_RE.finditer(text or ""):
        candidate = match.group(0).rstrip(").,]>")
        try:
            normalize_source_url(candidate)
        except SheetAnalysisError:
            continue
        return candidate
    return None


def _resolve_document_url(text: str, context_text: str | None = None) -> str | None:
    """Resolve a supported document URL from the current message or recent context."""
    return _extract_supported_document_url(text) or _extract_supported_document_url(
        context_text or ""
    )


def _is_direct_document_request(text: str) -> bool:
    """Decide whether to answer from the document directly instead of the LLM path."""
    url = _extract_supported_document_url(text)
    if not url:
        return False

    normalized = re.sub(r"\s+", " ", (text or "").lower()).strip()
    if any(marker in normalized for marker in REDDIT_HINTS):
        return False

    without_urls = URL_RE.sub("", normalized).strip()
    if not without_urls:
        return True
    if any(hint in normalized for hint in DIRECT_READ_HINTS):
        return True

    return len(without_urls.split()) <= 4


def _is_document_export_request(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", (text or "").lower()).strip()
    return any(keyword in normalized for keyword in DIRECT_EXPORT_KEYWORDS)


def _extract_google_sheet_export_url(url: str) -> str | None:
    """Convert a Google Sheets edit/view URL into a CSV export URL."""
    match = GOOGLE_SHEET_ID_RE.search(url)
    if not match:
        return None

    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    fragment = parse_qs(parsed.fragment)
    gid = (
        (query.get("gid") or fragment.get("gid") or ["0"])[0].strip()
        or "0"
    )
    sheet_id = match.group(1)
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def _looks_like_html(text: str) -> bool:
    """Detect HTML fallback pages such as auth or interstitial screens."""
    sample = text.lstrip().lower()
    return sample.startswith("<!doctype html") or sample.startswith("<html")


def _clip_cell(value: str) -> str:
    """Keep cell values compact so prompt previews stay readable."""
    compact = re.sub(r"\s+", " ", value or "").strip()
    if len(compact) <= 80:
        return compact
    return compact[:77].rstrip() + "..."


def _build_csv_prompt_context(source_url: str, csv_text: str) -> str | None:
    """Turn a CSV export into a compact prompt block."""
    try:
        reader = csv.reader(io.StringIO(csv_text))
        rows = []
        for row in reader:
            rows.append(row[:DOCUMENT_PREVIEW_COL_LIMIT])
            if len(rows) >= DOCUMENT_PREVIEW_ROW_LIMIT + 1:
                break
    except Exception:
        return None

    if not rows:
        return None

    header = [_clip_cell(value) for value in rows[0]]
    data_rows = rows[1:]
    preview_lines = [
        "Document access result: Public Google Sheet fetch succeeded.",
        "Use the fetched sheet contents below instead of saying access is blocked.",
        f"Source URL: {source_url}",
        f"Detected format: Google Sheet exported as CSV",
        f"Header columns: {' | '.join(header) if header else '(no header detected)'}",
        "Preview rows:",
    ]

    if not data_rows:
        preview_lines.append("(no data rows found)")
    else:
        for index, row in enumerate(data_rows, start=1):
            clipped_row = [_clip_cell(value) for value in row]
            preview_lines.append(f"{index}. {' | '.join(clipped_row)}")

    context = "\n".join(preview_lines).strip()
    if len(context) <= DOCUMENT_PREVIEW_CHAR_LIMIT:
        return context
    return context[: DOCUMENT_PREVIEW_CHAR_LIMIT - 3].rstrip() + "..."


def _clip_value(value: object, limit: int = 80) -> str:
    compact = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _source_kind_label(source_kind: str) -> str:
    return {
        "google_sheet": "Google Sheet",
        "csv": "CSV file",
        "excel": "Excel file",
    }.get(source_kind, "Document")


def _render_sample_row(columns: list[str], row: dict[str, object]) -> str:
    cells: list[str] = []
    for column in columns[:DIRECT_PREVIEW_COL_LIMIT]:
        value = row.get(column)
        if value in {None, ""}:
            continue
        cells.append(f"`{column}`: {_clip_value(value, limit=60)}")
    return ", ".join(cells) if cells else "(empty row)"


def _build_direct_document_message(result: dict[str, object]) -> str:
    source = dict(result.get("source") or {})
    columns = [str(column) for column in (result.get("columns") or [])]
    rows = list(result.get("rows") or [])
    summary = dict(result.get("summary") or {})
    insights = dict(result.get("insights") or {})
    column_types = dict(summary.get("column_types") or {})
    patterns = [str(pattern) for pattern in (insights.get("patterns") or []) if str(pattern).strip()]
    missing_values = dict(insights.get("missing_values") or {})

    row_count = int(summary.get("row_count") or 0)
    truncated = bool(summary.get("truncated"))
    lines = [
        "Document Read",
        "",
        f"*Status:* Read successfully",
        f"*Source:* {_source_kind_label(str(source.get('source_kind') or 'document'))}",
        f"*Rows Analyzed:* {row_count}",
        f"*Columns:* {len(columns)}",
        "",
        "*Summary*",
    ]

    if columns:
        shown_columns = ", ".join(f"`{column}`" for column in columns[:DIRECT_TYPE_LIMIT])
        extra_columns = len(columns) - min(len(columns), DIRECT_TYPE_LIMIT)
        if extra_columns > 0:
            shown_columns = f"{shown_columns}, and {extra_columns} more"
        lines.append(f"- Parsed columns: {shown_columns}.")

    if missing_values:
        top_missing = sorted(
            missing_values.items(),
            key=lambda item: float(dict(item[1]).get("ratio") or 0),
            reverse=True,
        )[:3]
        missing_summary = ", ".join(
            f"`{column}` ({int(dict(details).get('count') or 0)} missing)"
            for column, details in top_missing
        )
        lines.append(f"- Highest missing-value columns: {missing_summary}.")

    if patterns:
        lines.append(f"- {patterns[0]}")
    if truncated:
        lines.append("- The analysis was truncated before reading the full dataset.")

    if column_types:
        lines.extend(["", "*Column Types*"])
        for column in columns[:DIRECT_TYPE_LIMIT]:
            lines.append(f"- `{column}`: {column_types.get(column, 'unknown')}")
        remaining = len(columns) - min(len(columns), DIRECT_TYPE_LIMIT)
        if remaining > 0:
            lines.append(f"- ...and {remaining} more columns.")

    if rows:
        lines.extend(["", "*Sample Rows*"])
        for index, row in enumerate(rows[:DIRECT_PREVIEW_ROW_LIMIT], start=1):
            lines.append(f"{index}. {_render_sample_row(columns, row)}")
    else:
        lines.extend(["", "*Sample Rows*", "- No data rows found."])

    if len(patterns) > 1:
        lines.extend(["", "*Patterns*"])
        for pattern in patterns[:3]:
            lines.append(f"- {pattern}")

    return "\n".join(lines).strip()


def _build_excel_payload(result: dict[str, object]) -> dict[str, object]:
    source = dict(result.get("source") or {})
    columns = [str(column) for column in (result.get("columns") or [])]
    rows = list(result.get("rows") or [])
    summary = dict(result.get("summary") or {})
    workbook_name = (
        str(source.get("spreadsheet_id") or source.get("source_kind") or "document_export")
        .strip()
        .replace(" ", "_")
    )
    sheet_name = str(source.get("sheet_name") or "Data").strip() or "Data"
    summary_text = (
        f"Exported {_source_kind_label(str(source.get('source_kind') or 'document')).lower()} "
        f"with {int(summary.get('row_count') or 0)} rows and {int(summary.get('column_count') or 0)} columns."
    )
    return {
        "workbook_name": workbook_name,
        "sheet_name": sheet_name,
        "summary": summary_text,
        "columns": columns,
        "rows": rows,
        "row_limit": None,
    }


def _build_excel_export_response(result: dict[str, object]) -> str:
    payload = _build_excel_payload(result)
    return (
        "Document Export Ready\n\n"
        "*Status:* Full document data prepared for Excel export.\n"
        f"*Rows:* {len(payload.get('rows') or [])}\n"
        f"*Columns:* {len(payload.get('columns') or [])}\n\n"
        f"```json\n{json.dumps(payload, ensure_ascii=True)}\n```"
    )


async def build_direct_document_reply(
    text: str,
    *,
    context_text: str | None = None,
) -> str | None:
    """Return a deterministic Slack reply for direct document-read requests."""
    if not _is_direct_document_request(text) and not _is_document_export_request(text):
        return None

    source_url = _resolve_document_url(text, context_text=context_text)
    if not source_url:
        return None

    try:
        result = await asyncio.to_thread(
            analyze_sheet,
            source_url,
        )
    except SheetAccessError:
        return (
            "I found the document link, but it is not publicly readable yet.\n\n"
            "Please enable `Anyone with the link` access and resend it."
        )
    except SheetGidError as exc:
        return (
            f"I could open the spreadsheet, but {str(exc).strip()}.\n\n"
            "Please open the correct tab and resend that exact link."
        )
    except SheetEmptyError:
        return "I could read the document, but it does not contain any rows yet."
    except SheetAnalysisError as exc:
        return (
            "I found the document link, but I could not parse it cleanly.\n\n"
            f"Details: `{_clip_value(str(exc), limit=220)}`"
        )

    if _is_document_export_request(text):
        return _build_excel_export_response(result)
    return _build_direct_document_message(result)


async def build_document_prompt_context(text: str) -> str:
    """Fetch prompt-ready context for public document URLs when supported."""
    source_url = _extract_google_sheet_url(text)
    if not source_url:
        return ""

    export_url = _extract_google_sheet_export_url(source_url)
    if not export_url:
        return ""

    timeout = aiohttp.ClientTimeout(total=DOCUMENT_FETCH_TIMEOUT_SECONDS)
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; SlackRedditAgent/1.0)",
        "Accept": "text/csv,text/plain;q=0.9,*/*;q=0.8",
    }

    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(export_url, allow_redirects=True) as response:
                if response.status >= 400:
                    return ""
                body = await response.text(errors="replace")
                content_type = (response.headers.get("content-type") or "").lower()
    except Exception:
        return ""

    if not body or _looks_like_html(body):
        return ""

    if "text/csv" not in content_type and "," not in body:
        return ""

    return _build_csv_prompt_context(source_url, body) or ""
