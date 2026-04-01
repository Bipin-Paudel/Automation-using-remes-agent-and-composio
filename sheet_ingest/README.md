# Sheet Ingest

Production-ready helpers for reading and analyzing:

- Google Sheets edit links
- Google Sheets CSV export links
- Excel `.xlsx` URLs

The active implementation in this repo is Python-based and returns this JSON shape:

```json
{
  "source": {
    "original_url": "https://...",
    "fetch_url": "https://...",
    "source_kind": "google_sheet",
    "source_format": "csv"
  },
  "columns": ["Column A", "Column B"],
  "rows": [
    {
      "Column A": "value",
      "Column B": 123
    }
  ],
  "summary": {
    "row_count": 1,
    "column_count": 2,
    "empty_sheet": false,
    "truncated": false,
    "column_types": {
      "Column A": "string",
      "Column B": "number"
    }
  },
  "insights": {
    "missing_values": {},
    "duplicate_rows": 0,
    "numeric_columns": {},
    "categorical_columns": {},
    "date_columns": {},
    "patterns": [
      "No strong anomalies detected in the sampled data."
    ]
  }
}
```

## What It Does

1. Validates the input URL.
2. Detects whether it is a Google Sheet, CSV URL, or `.xlsx` file.
3. Converts Google Sheets edit links into a CSV export URL.
4. Detects private Sheets and returns:

```text
Please enable 'Anyone with the link' access
```

5. Parses data into `columns` and `rows`.
6. Adds summary and lightweight insights.

## Python

File: [python_sheet_reader.py](/Users/bipinpaudel/work/automation/sheet_ingest/python_sheet_reader.py)

### Install

```bash
uv sync
```

### Usage

```python
from sheet_ingest import analyzeSheet

result = analyzeSheet(
    "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit?gid=0#gid=0",
    gid="0",
    max_rows=500,
)

print(result["summary"])
print(result["rows"][:3])
```

### CLI

```bash
uv run python -m sheet_ingest.python_sheet_reader "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit?gid=0#gid=0" --gid 0 --max-rows 100
```

### API Integration

```python
from sheet_ingest import analyze_sheet_request

def handle_request(payload: dict) -> dict:
    return analyze_sheet_request(payload)
```

Example payload:

```json
{
  "url": "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit?gid=0#gid=0",
  "gid": "0",
  "max_rows": 100
}
```

## Edge Cases Covered

- Invalid URL
- Private Google Sheet
- Wrong Google Sheet `gid`
- Empty sheet
- Large downloads
- Optional row truncation for large datasets

## Notes

- Google Sheets require public link access for direct export.
- Excel URLs must point directly to a downloadable `.xlsx` file.
- For very large datasets, use `max_rows` in the response layer.
- The Slack bot currently uses the Python implementation directly.
