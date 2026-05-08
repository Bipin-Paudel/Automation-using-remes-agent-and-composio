import asyncio
import json
import re

from sheet_document_ingest import (
    SheetAccessError,
    SheetAnalysisError,
    SheetEmptyError,
    SheetGidError,
    analyze_sheet,
    normalize_source_url,
)

URL_RE = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)
DIRECT_PREVIEW_ROW_LIMIT = 3
DIRECT_PREVIEW_COL_LIMIT = 6
DIRECT_TYPE_LIMIT = 8
DIRECT_EXPORT_KEYWORDS = (
    "excel",
    "xlsx",
    "docx",
    "word file",
    "doc file",
    "document file",
    "new document file",
    "new docs file",
    "generate doc",
    "generate docs",
    "create doc",
    "create docs",
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


def _extract_supported_document_url(text: str) -> str | None:
    """Return the first supported sheet or document URL."""
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


def is_direct_document_flow(text: str) -> bool:
    """Return whether the message should use the direct document flow."""
    return _is_direct_document_request(text) or _is_document_export_request(text)


def _prefers_excel_export(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", (text or "").lower()).strip()
    return any(keyword in normalized for keyword in ("excel", "xlsx", "spreadsheet"))


def _prefers_docx_export(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", (text or "").lower()).strip()
    return any(
        keyword in normalized
        for keyword in (
            "docx",
            "word",
            "doc file",
            "document file",
            "docs file",
            "generate doc",
            "create doc",
        )
    )


def _clip_value(value: object, limit: int = 80) -> str:
    compact = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _source_kind_label(source_kind: str) -> str:
    return {
        "google_sheet": "Google Sheet",
        "google_doc": "Google Doc",
        "csv": "CSV file",
        "excel": "Excel file",
        "docx": "Word document",
        "text_document": "Text document",
    }.get(source_kind, "Document")


def _source_unit_label(source_kind: str) -> str:
    return {
        "google_doc": "Paragraphs Analyzed",
        "docx": "Paragraphs Analyzed",
        "text_document": "Paragraphs Analyzed",
    }.get(source_kind, "Rows Analyzed")


def _is_text_document_source(source_kind: str) -> bool:
    return source_kind in {"google_doc", "docx", "text_document"}


def _doc_paragraphs(rows: list[dict[str, object]]) -> list[str]:
    paragraphs: list[str] = []
    for row in rows:
        content = str(row.get("content") or "").strip()
        if content:
            paragraphs.append(content)
    return paragraphs


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
    source_kind = str(source.get("source_kind") or "document")
    if _is_text_document_source(source_kind):
        return _build_text_document_message(result)

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
        f"*Source:* {_source_kind_label(source_kind)}",
        f"*{_source_unit_label(source_kind)}:* {row_count}",
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


def _build_text_document_message(result: dict[str, object]) -> str:
    source = dict(result.get("source") or {})
    rows = list(result.get("rows") or [])
    summary = dict(result.get("summary") or {})
    insights = dict(result.get("insights") or {})
    patterns = [str(pattern) for pattern in (insights.get("patterns") or []) if str(pattern).strip()]
    paragraphs = _doc_paragraphs(rows)
    paragraph_count = int(summary.get("row_count") or len(paragraphs))
    total_words = sum(int(row.get("word_count") or 0) for row in rows)
    truncated = bool(summary.get("truncated"))
    source_kind = str(source.get("source_kind") or "document")

    lines = [
        "Document Read",
        "",
        f"*Status:* Read successfully",
        f"*Source:* {_source_kind_label(source_kind)}",
        f"*Paragraphs:* {paragraph_count}",
        f"*Words:* {total_words}",
        "",
        "*Summary*",
    ]

    if paragraphs:
        preview = _clip_value(paragraphs[0], limit=220)
        lines.append(f"- Opening text: {preview}")
    if len(paragraphs) > 1:
        lines.append(f"- The document contains {paragraph_count} readable paragraph(s).")
    if patterns:
        lines.append(f"- {patterns[0]}")
    if truncated:
        lines.append("- The analysis was truncated before reading the full document.")

    lines.extend(["", "*Text Preview*"])
    if paragraphs:
        for index, paragraph in enumerate(paragraphs[:DIRECT_PREVIEW_ROW_LIMIT], start=1):
            lines.append(f"{index}. {_clip_value(paragraph, limit=320)}")
    else:
        lines.append("- No readable paragraphs found.")

    return "\n".join(lines).strip()


def _build_excel_payload(result: dict[str, object]) -> dict[str, object]:
    source = dict(result.get("source") or {})
    columns = [str(column) for column in (result.get("columns") or [])]
    rows = list(result.get("rows") or [])
    summary = dict(result.get("summary") or {})
    workbook_name = (
        str(
            source.get("spreadsheet_id")
            or source.get("document_id")
            or source.get("source_kind")
            or "document_export"
        )
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


def _build_docx_payload(result: dict[str, object]) -> dict[str, object]:
    source = dict(result.get("source") or {})
    rows = list(result.get("rows") or [])
    summary = dict(result.get("summary") or {})
    document_name = (
        str(source.get("document_id") or source.get("source_kind") or "document_export")
        .strip()
        .replace(" ", "_")
    )
    title = str(source.get("document_id") or "Document Export").strip() or "Document Export"
    paragraphs = _doc_paragraphs(rows)
    summary_text = (
        f"Exported {_source_kind_label(str(source.get('source_kind') or 'document')).lower()} "
        f"with {int(summary.get('row_count') or 0)} paragraph(s)."
    )
    return {
        "export_type": "docx",
        "document_name": document_name,
        "title": title,
        "summary": summary_text,
        "paragraphs": paragraphs,
    }


def _build_docx_export_response(result: dict[str, object]) -> str:
    payload = _build_docx_payload(result)
    return (
        "Document Export Ready\n\n"
        "*Status:* Full document text prepared for DOCX export.\n"
        f"*Paragraphs:* {len(payload.get('paragraphs') or [])}\n\n"
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
        return "I could read the document, but it does not contain any readable content yet."
    except SheetAnalysisError as exc:
        return (
            "I found the document link, but I could not parse it cleanly.\n\n"
            f"Details: `{_clip_value(str(exc), limit=220)}`"
        )

    if _is_document_export_request(text):
        source_kind = str(dict(result.get("source") or {}).get("source_kind") or "")
        if _is_text_document_source(source_kind) and (
            _prefers_docx_export(text) or not _prefers_excel_export(text)
        ):
            return _build_docx_export_response(result)
        return _build_excel_export_response(result)
    return _build_direct_document_message(result)


async def build_document_prompt_context(text: str) -> str:
    """Fetch prompt-ready context for public document URLs when supported."""
    source_url = _extract_supported_document_url(text)
    if not source_url:
        return ""

    try:
        result = await asyncio.to_thread(analyze_sheet, source_url, max_rows=12)
    except Exception:
        return ""

    source = dict(result.get("source") or {})
    columns = [str(column) for column in (result.get("columns") or [])]
    rows = list(result.get("rows") or [])
    summary = dict(result.get("summary") or {})
    source_kind = str(source.get("source_kind") or "document")

    lines = [
        "Document access result: Public document fetch succeeded.",
        "Use the fetched document contents below instead of saying access is blocked.",
        f"Source URL: {source_url}",
        f"Detected format: {_source_kind_label(source_kind)}",
        f"Rows captured: {int(summary.get('row_count') or 0)}",
        f"Columns: {', '.join(columns[:DIRECT_TYPE_LIMIT]) if columns else '(none)'}",
        "Preview rows:",
    ]

    if not rows:
        lines.append("(no rows found)")
    else:
        for index, row in enumerate(rows[:DIRECT_PREVIEW_ROW_LIMIT], start=1):
            lines.append(f"{index}. {_render_sample_row(columns, row)}")

    return "\n".join(lines).strip()
