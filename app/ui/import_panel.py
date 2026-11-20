"""Excel import tab: preview parsed rows and QA issues before committing."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QVBoxLayout, QWidget,
)

from ..db import counts
from ..i18n import tr
from ..importer import parse_workbook, write_to_db
from .common import set_row, setup_table

PREVIEW_COLUMNS = ["section", "code", "item", "serial_placeholder", "department", "location", "qty"]


class ImportPanel(QWidget):
    imported = Signal()

    def __init__(self, conn: sqlite3.Connection, lang: str = "ar", parent=None):
        super().__init__(parent)
        self.conn, self.lang = conn, lang
        self.result = None
        self._build()

    def _build(self) -> None:
        self.setLayoutDirection(
            Qt.LayoutDirection.RightToLeft if self.lang == "ar" else Qt.LayoutDirection.LeftToRight
        )
        root = QVBoxLayout(self)
        root.addWidget(QLabel(tr("import_hint", self.lang)))

        pick = QHBoxLayout()
        self.edit_path = QLineEdit()
        self.edit_path.setReadOnly(True)
        self.btn_browse = QPushButton(tr("browse", self.lang))
        self.btn_browse.clicked.connect(self.browse)
        self.btn_preview = QPushButton(tr("preview", self.lang))
        self.btn_preview.clicked.connect(self.preview)
        self.btn_import = QPushButton(tr("do_import", self.lang))
        self.btn_import.clicked.connect(self.do_import)
        self.btn_import.setEnabled(False)
        pick.addWidget(self.edit_path)
        pick.addWidget(self.btn_browse)
        pick.addWidget(self.btn_preview)
        pick.addWidget(self.btn_import)
        root.addLayout(pick)

        self.lbl_summary = QLabel()
        root.addWidget(self.lbl_summary)

        self.table = QTableWidget()
        setup_table(self.table, [tr(c, self.lang) for c in PREVIEW_COLUMNS])
        root.addWidget(self.table, stretch=1)

        self.lbl_issues = QLabel()
        root.addWidget(self.lbl_issues)

    def browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, tr("select_file", self.lang), "", "Excel (*.xlsx *.xlsm)"
        )
        if path:
            self.edit_path.setText(path)
            self.preview()

    def preview(self) -> None:
        path = self.edit_path.text()
        if not path or not Path(path).exists():
            QMessageBox.warning(self, tr("error", self.lang), tr("select_file", self.lang))
            return
        try:
            self.result = parse_workbook(path)
        except Exception as exc:
            QMessageBox.critical(self, tr("error", self.lang), str(exc))
            return
        self.btn_import.setEnabled(True)
        totals = self.result.totals
        self.lbl_summary.setText(
            f"devices={totals.get('devices', 0)}   furniture={totals.get('furniture', 0)}   "
            f"network={totals.get('network', 0)}   electrical={totals.get('electrical', 0)}   "
            f"total={totals.get('total', 0)}"
        )
        preview_rows = self.result.assets[:150]
        self.table.setRowCount(len(preview_rows))
        for i, a in enumerate(preview_rows):
            set_row(self.table, i, [
                tr(a.section, self.lang), f"r{a.source_row}", a.name_ar,
                a.serial_number, a.department, a.location or a.area_ar, a.quantity,
            ])
        self.lbl_issues.setText(
            f"{tr('unresolved', self.lang)}: {len(self.result.issues)}"
        )

    def do_import(self) -> None:
        if not self.result:
            return
        path = Path(self.edit_path.text())
        answer = QMessageBox.question(
            self, tr("do_import", self.lang),
            f"{path.name}\n{self.result.totals.get('total', 0)} rows\nContinue?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        batch_id = write_to_db(self.result, self.conn, path.name)
        self.lbl_summary.setText(f"{tr('imported', self.lang)} #{batch_id} — {counts(self.conn)}")
        self.imported.emit()
