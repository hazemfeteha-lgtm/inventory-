"""Shared search query builder (used by UI, Excel export and PDF report)."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .normalize import norm


@dataclass
class SearchFilters:
    section: str = ""
    department_id: int | None = None
    location_id: int | None = None
    category_id: int | None = None
    text: str = ""
    serial: str = ""
    issues_only: bool = False


SELECT_SQL = """
SELECT a.*,
       c.name_ar AS category_ar, c.name_en AS category_en,
       d.name_ar AS dept_ar, d.name_en AS dept_en,
       l.name_ar AS loc_ar, l.name_en AS loc_en
FROM assets a
LEFT JOIN categories c ON c.id = a.category_id
LEFT JOIN departments d ON d.id = a.department_id
LEFT JOIN locations l ON l.id = a.location_id
"""


def find_assets(conn: sqlite3.Connection, f: SearchFilters) -> list[sqlite3.Row]:
    where: list[str] = []
    params: list[object] = []
    if f.section:
        where.append("a.section = ?")
        params.append(f.section)
    if f.department_id:
        where.append("a.department_id = ?")
        params.append(f.department_id)
    if f.location_id:
        where.append("a.location_id = ?")
        params.append(f.location_id)
    if f.category_id:
        where.append("a.category_id = ?")
        params.append(f.category_id)
    if f.text:
        where.append("a.search_key LIKE ?")
        params.append(f"%{norm(f.text)}%")
    if f.serial:
        where.append("(a.serial_number LIKE ? OR a.search_key LIKE ?)")
        params.extend([f"%{f.serial.strip()}%", f"%{norm(f.serial)}%"])
    if f.issues_only:
        where.append("EXISTS (SELECT 1 FROM quality_issues q WHERE q.asset_id = a.id AND q.resolved = 0)")
    sql = SELECT_SQL
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY a.section, d.name_ar, l.name_ar, a.id"
    return conn.execute(sql, params).fetchall()


def get_asset(conn: sqlite3.Connection, asset_id: int) -> sqlite3.Row | None:
    return conn.execute(SELECT_SQL + " WHERE a.id = ?", (asset_id,)).fetchone()
