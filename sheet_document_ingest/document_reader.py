from __future__ import annotations

import io
import re
import zipfile
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import pandas as pd

from .sheet_reader import (
    NormalizedSource,
    ParsedFrame,
    SheetAnalysisError,
    SheetEmptyError,
    _build_result,
    _download_source,
    _probe_row_limit,
    _validate_max_rows,
)

GOOGLE_DOC_ID_RE = re.compile(r"/document/d/([a-zA-Z0-9\-_]+)")


def match_document_source(url: str) -> NormalizedSource | None:
    """Return a normalized document-like source when the URL matches one."""
    parsed = urlparse(url)
    hostname = parsed.netloc.lower()
    path = parsed.path.lower()

    if hostname == "docs.google.com" and "/document/" in path:
        match = GOOGLE_DOC_ID_RE.search(url)
        if not match:
            raise SheetAnalysisError("Invalid Google Docs URL.")
        document_id = match.group(1)
        export_url = f"https://docs.google.com/document/d/{document_id}/export?format=txt"
        return NormalizedSource(
            original_url=url,
            fetch_url=export_url,
            source_kind="google_doc",
            source_format="txt",
            document_id=document_id,
        )

    if path.endswith(".docx"):
        return NormalizedSource(
            original_url=url,
            fetch_url=url,
            source_kind="docx",
            source_format="docx",
        )

    if path.endswith(".txt") or path.endswith(".md"):
        return NormalizedSource(
            original_url=url,
            fetch_url=url,
            source_kind="text_document",
            source_format="txt",
        )

    return None


def _clean_document_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\ufeff", "").replace("\u00a0", " ")
    return normalized.strip()


def _document_records_to_frame(records: list[dict[str, Any]]) -> ParsedFrame:
    dataframe = pd.DataFrame.from_records(
        records,
        columns=("paragraph_number", "content", "word_count", "character_count"),
    )
    return ParsedFrame(dataframe=dataframe, sheet_name="Document")


def _parse_text_document_bytes(payload: bytes, *, nrows: int | None = None) -> ParsedFrame:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        text = payload.decode("utf-8", errors="replace")

    normalized_text = _clean_document_text(text)
    if not normalized_text:
        raise SheetEmptyError("The document is empty.")

    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n+", normalized_text)
        if paragraph.strip()
    ]
    if not paragraphs:
        paragraphs = [line.strip() for line in normalized_text.splitlines() if line.strip()]
    if not paragraphs:
        raise SheetEmptyError("The document is empty.")

    if nrows is not None:
        paragraphs = paragraphs[:nrows]

    records: list[dict[str, Any]] = []
    for index, paragraph in enumerate(paragraphs, start=1):
        records.append(
            {
                "paragraph_number": index,
                "content": paragraph,
                "word_count": len(paragraph.split()),
                "character_count": len(paragraph),
            }
        )
    return _document_records_to_frame(records)


def _extract_docx_paragraphs(payload: bytes) -> list[str]:
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            document_xml = archive.read("word/document.xml")
    except KeyError as exc:
        raise SheetAnalysisError("The .docx file is missing word/document.xml.") from exc
    except zipfile.BadZipFile as exc:
        raise SheetAnalysisError("The .docx file is not a valid Word document.") from exc

    try:
        root = ET.fromstring(document_xml)
    except ET.ParseError as exc:
        raise SheetAnalysisError("Failed to parse the .docx XML content.") from exc

    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        text_parts = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
        combined = "".join(text_parts).strip()
        if combined:
            paragraphs.append(combined)
    return paragraphs


def _parse_docx_bytes(payload: bytes, *, nrows: int | None = None) -> ParsedFrame:
    paragraphs = _extract_docx_paragraphs(payload)
    if not paragraphs:
        raise SheetEmptyError("The document is empty.")

    if nrows is not None:
        paragraphs = paragraphs[:nrows]

    records: list[dict[str, Any]] = []
    for index, paragraph in enumerate(paragraphs, start=1):
        records.append(
            {
                "paragraph_number": index,
                "content": paragraph,
                "word_count": len(paragraph.split()),
                "character_count": len(paragraph),
            }
        )
    return _document_records_to_frame(records)


def analyze_document_source(
    source: NormalizedSource,
    *,
    max_rows: int | None = None,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """Fetch, parse, and analyze a document-like source."""
    validated_max_rows = _validate_max_rows(max_rows)
    payload, content_type, final_url = _download_source(
        source,
        timeout_seconds=timeout_seconds,
    )
    row_probe_limit = _probe_row_limit(validated_max_rows)

    if source.source_format == "txt":
        parsed = _parse_text_document_bytes(payload, nrows=row_probe_limit)
    elif source.source_format == "docx":
        parsed = _parse_docx_bytes(payload, nrows=row_probe_limit)
    else:
        raise SheetAnalysisError("Unsupported document response format.")

    return _build_result(
        source,
        parsed,
        content_type=content_type,
        final_url=final_url,
        validated_max_rows=validated_max_rows,
    )
