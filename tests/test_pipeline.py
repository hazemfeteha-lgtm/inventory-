"""Regression checks for the import -> search -> export pipeline."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db import connect, counts, init_db, norm
from app.exporter import export_excel
from app.importer import parse_workbook, write_to_db
from app.search import SearchFilters, find_assets

SOURCE = Path("/root/chat/inbox/حصر مركز  خدمات مصر الاسكندريه.xlsx")


def test_parse_counts():
    result = parse_workbook(SOURCE)
    assert result.totals["devices"] == 187
    assert result.totals["furniture"] == 189
    assert result.totals["network"] == 19
    assert result.totals["electrical"] == 74
    kinds = {i["issue_type"] for i in result.issues}
    assert {"duplicate_serial", "missing_quantity", "total_mismatch"} <= kinds


def test_database_roundtrip(tmp_path):
    db = tmp_path / "t.db"
    conn = connect(db)
    init_db(conn)
    result = parse_workbook(SOURCE)
    write_to_db(result, conn, SOURCE.name)
    assert counts(conn)["total"] == 469
    rows = find_assets(conn, SearchFilters(section="devices", serial="PC29SJNE"))
    assert len(rows) == 2  # both duplicate rows kept, each flagged
    assert len(find_assets(conn, SearchFilters(text="كرسى"))) >= 10  # Arabic variant search
    assert len(find_assets(conn, SearchFilters(issues_only=True))) >= 10
    out = tmp_path / "out.xlsx"
    export_excel(find_assets(conn, SearchFilters()), out)
    assert out.exists()
    conn.close()


if __name__ == "__main__":
    import tempfile

    test_parse_counts()
    with tempfile.TemporaryDirectory() as directory:
        test_database_roundtrip(Path(directory))
    print("All pipeline checks passed.")
