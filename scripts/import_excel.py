"""CLI: parse the source workbook, print a QA report, optionally write to SQLite.

Usage:
    python scripts/import_excel.py [path/to/file.xlsx] [--write] [--db path/to/inventory.db]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import connect, counts, init_db
from app.importer import parse_workbook, write_to_db

DEFAULT = Path("/root/chat/inbox/حصر مركز  خدمات مصر الاسكندريه.xlsx")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import center inventory Excel into SQLite")
    parser.add_argument("file", nargs="?", default=str(DEFAULT))
    parser.add_argument("--write", action="store_true", help="write parsed data into the database")
    parser.add_argument("--db", default=None)
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    result = parse_workbook(path)
    print(f"File: {path.name}")
    print("Parsed rows:", result.totals)
    print("\nSample per section:")
    for section in ("devices", "furniture", "network", "electrical"):
        sample = [a for a in result.assets if a.section == section][:4]
        for a in sample:
            print(f"  [{section}] r{a.source_row} dept={a.department!r} loc={a.location!r} "
                  f"item={a.name_ar!r} serial={a.serial_number!r} qty={a.quantity}")

    print(f"\nData-quality issues ({len(result.issues)}):")
    for issue in result.issues[:40]:
        print(f"  {issue['issue_type']:<20} {issue['source_sheet'][:18]:<18} "
              f"r{issue['source_row']:<4} {issue['detail_en']}")

    if args.write:
        conn = connect(args.db)
        init_db(conn)
        batch_id = write_to_db(result, conn, path.name)
        conn.close()
        print(f"\nWrote batch #{batch_id}. Counts: {counts(connect(args.db))}")
    else:
        print("\n(dry run - pass --write to store the data)")


if __name__ == "__main__":
    main()
