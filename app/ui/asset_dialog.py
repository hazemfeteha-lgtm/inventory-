"""Read-only detail dialog for one asset, including its movement history."""
from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFormLayout, QLabel, QTabWidget, QTableWidget, QVBoxLayout

from ..i18n import tr
from .common import set_row, setup_table

FIELD_KEYS = [
    "code", "item", "item_en", "section", "category", "serial_placeholder",
    "brand", "department", "location", "qty", "notes",
]


class AssetDialog(QDialog):
    def __init__(self, conn: sqlite3.Connection, asset_id: int, lang: str = "ar", parent=None):
        super().__init__(parent)
        self.conn, self.lang = conn, lang
        self.setWindowTitle(tr("details", lang))
        self.resize(560, 460)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if lang == "ar" else Qt.LayoutDirection.LeftToRight)

        row = conn.execute(
            """SELECT a.*, c.name_ar category_ar, c.name_en category_en,
                      d.name_ar dept_ar, l.name_ar loc_ar
               FROM assets a
               LEFT JOIN categories c ON c.id=a.category_id
               LEFT JOIN departments d ON d.id=a.department_id
               LEFT JOIN locations l ON l.id=a.location_id
               WHERE a.id=?""",
            (asset_id,),
        ).fetchone()

        tabs = QTabWidget()
        from PySide6.QtWidgets import QWidget

        details = QWidget()
        form = QFormLayout(details)
        values = {
            "code": row["asset_code"] or "",
            "item": row["name_ar"],
            "item_en": row["name_en"],
            "section": tr(row["section"], lang),
            "category": (row["category_ar"] if lang == "ar" else row["category_en"]) or "",
            "serial_placeholder": row["serial_number"],
            "brand": row["brand_model"],
            "department": row["dept_ar"] or "",
            "location": row["loc_ar"] or "",
            "qty": row["quantity"],
            "notes": row["notes"],
        }
        for key in FIELD_KEYS:
            form.addRow(tr(key, lang) + ":", QLabel(str(values[key])))
        tabs.addTab(details, tr("details", lang))

        moves = QTableWidget()
        setup_table(moves, [tr(x, lang) for x in ("department", "location", "generated", "notes")])
        history = conn.execute(
            """SELECT d.name_ar dept, l.name_ar loc, m.moved_at, m.note
               FROM movements m
               LEFT JOIN departments d ON d.id=m.to_department_id
               LEFT JOIN locations l ON l.id=m.to_location_id
               WHERE m.asset_id=? ORDER BY m.id DESC""",
            (asset_id,),
        ).fetchall()
        moves.setRowCount(len(history))
        for i, m in enumerate(history):
            set_row(moves, i, [m["dept"], m["loc"], m["moved_at"], m["note"]])
        tabs.addTab(moves, tr("movements", lang))

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
