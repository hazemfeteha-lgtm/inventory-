"""Dashboard tab: high-level counts from the current database."""
from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QTableWidget, QVBoxLayout, QWidget

from ..db import counts
from ..i18n import tr
from .common import set_row, setup_table


class Dashboard(QWidget):
    def __init__(self, conn: sqlite3.Connection, lang: str = "ar", parent=None):
        super().__init__(parent)
        self.conn, self.lang = conn, lang
        root = QGridLayout(self)
        self.setLayoutDirection(
            Qt.LayoutDirection.RightToLeft if self.lang == "ar" else Qt.LayoutDirection.LeftToRight
        )

        self.cards = QGroupBox(tr("total_assets", self.lang))
        card_layout = QVBoxLayout(self.cards)
        self.lbl_total = QLabel()
        self.lbl_total.setStyleSheet("font-size:26px; font-weight:bold; color:#2f6da3;")
        card_layout.addWidget(self.lbl_total)
        self.lbl_batches = QLabel()
        card_layout.addWidget(self.lbl_batches)
        root.addWidget(self.cards, 0, 0)

        self.table = QTableWidget()
        setup_table(self.table, [tr("by_department", self.lang), tr("count", self.lang)])
        root.addWidget(self.table, 0, 1, 2, 1)

        self.locations = QTableWidget()
        setup_table(self.locations, [tr("by_location", self.lang), tr("count", self.lang)])
        root.addWidget(self.locations, 1, 0)
        self.refresh()

    def refresh(self) -> None:
        c = counts(self.conn)
        self.lbl_total.setText(
            f"{c.get('total', 0)}\n"
            f"{tr('devices', self.lang)}: {c.get('devices', 0)}  |  "
            f"{tr('furniture', self.lang)}: {c.get('furniture', 0)}\n"
            f"{tr('electrical', self.lang)}: {c.get('electrical', 0)}  |  "
            f"{tr('network', self.lang)}: {c.get('network', 0)}"
        )
        self.lbl_batches.setText(f"{tr('import_batches', self.lang)}: {c.get('batches', 0)}")
        depts = self.conn.execute(
            """SELECT d.name_ar name, COUNT(*) n FROM assets a
               JOIN departments d ON d.id=a.department_id
               GROUP BY d.id ORDER BY n DESC LIMIT 15"""
        ).fetchall()
        self.table.setRowCount(len(depts))
        for i, r in enumerate(depts):
            set_row(self.table, i, [r["name"], r["n"]])
        locs = self.conn.execute(
            """SELECT l.name_ar name, COUNT(*) n FROM assets a
               JOIN locations l ON l.id=a.location_id
               GROUP BY l.id ORDER BY n DESC LIMIT 15"""
        ).fetchall()
        self.locations.setRowCount(len(locs))
        for i, r in enumerate(locs):
            set_row(self.locations, i, [r["name"], r["n"]])
