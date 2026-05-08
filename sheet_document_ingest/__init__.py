from .document_reader import analyze_document_source, match_document_source
from .sheet_reader import (
    SheetAccessError,
    SheetAnalysisError,
    SheetEmptyError,
    SheetGidError,
    _validate_url,
    analyze_sheet_source,
    is_sheet_source_kind,
    match_sheet_source,
)


def normalize_source_url(
    url: str,
    *,
    gid: str | None = None,
):
    """Normalize a supported sheet or document URL into a fetchable source."""
    clean_url = _validate_url(url)
    source = match_sheet_source(clean_url, gid=gid)
    if source:
        return source

    source = match_document_source(clean_url)
    if source:
        return source

    raise SheetAnalysisError(
        "Unsupported URL. Use a Google Sheets link, Google Docs link, CSV export link, text file URL, .docx file URL, or .xlsx file URL."
    )


def analyze_sheet(
    url: str,
    *,
    gid: str | None = None,
    sheet_name: str | int | None = None,
    max_rows: int | None = None,
    timeout_seconds: int = 30,
) -> dict:
    """Fetch, parse, and analyze a supported sheet or document URL."""
    source = normalize_source_url(url, gid=gid)
    if is_sheet_source_kind(source.source_kind):
        return analyze_sheet_source(
            source,
            sheet_name=sheet_name,
            max_rows=max_rows,
            timeout_seconds=timeout_seconds,
        )
    return analyze_document_source(
        source,
        max_rows=max_rows,
        timeout_seconds=timeout_seconds,
    )


def analyzeSheet(url: str, **kwargs):
    """CamelCase wrapper for parity with older usage."""
    return analyze_sheet(url, **kwargs)


def analyze_sheet_request(payload: dict) -> dict:
    """API-friendly wrapper that accepts a JSON-like request payload."""
    return analyze_sheet(
        payload.get("url", ""),
        gid=payload.get("gid"),
        sheet_name=payload.get("sheet_name"),
        max_rows=payload.get("max_rows"),
        timeout_seconds=payload.get("timeout_seconds", 30),
    )

__all__ = [
    "SheetAccessError",
    "SheetAnalysisError",
    "SheetEmptyError",
    "SheetGidError",
    "analyzeSheet",
    "analyze_sheet",
    "analyze_sheet_request",
    "normalize_source_url",
]
