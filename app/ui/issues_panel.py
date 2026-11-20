"""Data-review tab: list and resolve flagged rows from Excel imports."""
from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QPushButton, QTableWidget, QVBoxLayout, QWidget

from ..i18n import tr
from .common import set_row, setup_table

COLUMNS = ["issue_type", "status", "source_sheet", "source_row", "notes"]


class IssuesPanel(QWidget):
    changed = Signal()

    def __init__(self, conn: sqlite3.Connection, lang: str = "ar", parent=None):
        super().__init__(parent)
        self.conn, self.lang = conn, lang
        self._build()
        self.refresh()

    def _build(self) -> None:
        self.setLayoutDirection(
            Qt.LayoutDirection.RightToLeft if self.lang == "ar" else Qt.LayoutDirection.LeftToRight
        )
        root = QVBoxLayout(self)
        self.table = QTableWidget()
        setup_table(self.table, [tr(c, self.lang) for c in COLUMNS])
        root.addWidget(self.table, stretch=1)
        bar = QHBoxLayout()
        self.lbl = QLabel()
        bar.addWidget(self.lbl)
        bar.addStretch()
        self.btn_resolve = QPushButton(tr("resolve", self.lang))
        self.btn_resolve.clicked.connect(self.resolve_selected)
        bar.addWidget(self.btn_resolve)
        root.addLayout(bar)

    def refresh(self) -> None:
        rows = self.conn.execute(
            """SELECT * FROM quality_issues
               ORDER BY resolved, source_sheet, source_row, id"""
        ).fetchall()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            detail = r["detail_ar"] if self.lang == "ar" else r["detail_en"]
            set_row(self.table, i, [
                r["issue_type"],
                tr("status", self.lang) + ": " + (tr("ready", self.lang) if r["resolved"] else tr("unresolved", self.lang)),
                r["source_sheet"], r["source_row"], detail,
            ])
        unresolved = sum(1 for r in rows if not r["resolved"])
        self.lbl.setText(f"{tr('unresolved', self.lang)}: {unresolved}")

    def resolve_selected(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        row_no = items[0].row()
        issue_type = self.table.item(row_no, 0).text()
        sheet = self.table.item(row_no, 2).text()
        source_row = self.table.item(row_no, 3).text()
        self.conn.execute(
            """UPDATE quality_issues SET resolved=1
               WHERE issue_type=? AND source_sheet=? AND CAST(source_row AS TEXT)=?""",
            (issue_type, sheet, source_row),
        )
        self.conn.commit()
        self.refresh()
        self.changed.emit()
