from __future__ import annotations

import json

from . import analyze_sheet
from .sheet_reader import _build_cli


def main() -> None:
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


if __name__ == "__main__":
    main()
