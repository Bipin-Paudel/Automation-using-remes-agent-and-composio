import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from .config import EXPORTS_DIR, MAX_EXPORT_ROWS


def sanitize_filename(value: str, fallback: str) -> str:
    """Create a filesystem-safe filename stem."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip()).strip("._")
    return cleaned or fallback


def sanitize_sheet_name(value: str) -> str:
    """Create an Excel-safe worksheet title."""
    cleaned = re.sub(r"[:\\\\/?*\\[\\]]", " ", value).strip()
    return (cleaned or "Report")[:31]


def coerce_excel_value(value: Any) -> Any:
    """Normalize nested data for a worksheet cell."""
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, ensure_ascii=True)


def extract_excel_payload(text: str) -> tuple[str, dict[str, Any] | None]:
    """Extract a JSON export block from an agent response if present."""
    code_block_pattern = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)

    for match in code_block_pattern.finditer(text):
        candidate = match.group(1).strip()
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue

        if not isinstance(payload, dict):
            continue

        rows = payload.get("rows")
        columns = payload.get("columns")
        if not isinstance(rows, list) or not isinstance(columns, list):
            continue

        message_text = text.replace(match.group(0), "").strip()
        return message_text, payload

    return text, None


def create_excel_report(payload: dict[str, Any]) -> Path:
    """Build an XLSX file from the agent export payload."""
    workbook_name = sanitize_filename(
        str(payload.get("workbook_name") or "reddit_report"),
        fallback="reddit_report",
    )
    sheet_name = sanitize_sheet_name(str(payload.get("sheet_name") or "Report"))
    summary = str(payload.get("summary") or "").strip()
    columns = [str(column).strip() for column in payload.get("columns", []) if str(column).strip()]
    raw_rows = payload.get("rows") or []
    row_limit = payload.get("row_limit", MAX_EXPORT_ROWS)

    rows: list[dict[str, Any]] = []
    row_source = raw_rows if row_limit is None else raw_rows[: int(row_limit)]
    for raw_row in row_source:
        if isinstance(raw_row, dict):
            rows.append(raw_row)

    if not columns and rows:
        columns = list(rows[0].keys())

    if not columns:
        columns = ["result"]

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_name
    worksheet.append(columns)

    for header_cell in worksheet[1]:
        header_cell.font = Font(bold=True)

    for row in rows:
        worksheet.append([coerce_excel_value(row.get(column, "")) for column in columns])

    for index, column in enumerate(columns, start=1):
        cell_values = [str(column)]
        for row in rows:
            cell_values.append(str(coerce_excel_value(row.get(column, ""))))
        width = min(max(len(value) for value in cell_values) + 2, 60)
        worksheet.column_dimensions[get_column_letter(index)].width = width

    if summary:
        summary_sheet = workbook.create_sheet(title="Summary")
        summary_sheet["A1"] = "Summary"
        summary_sheet["A1"].font = Font(bold=True)
        summary_sheet["A2"] = summary
        summary_sheet.column_dimensions["A"].width = 100

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = EXPORTS_DIR / f"{workbook_name}_{timestamp}.xlsx"
    workbook.save(file_path)
    return file_path
