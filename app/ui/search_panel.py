"""Advanced search tab with segmented filters, results and exports."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QFileDialog, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget, QVBoxLayout, QWidget,
)

from ..exporter import export_excel, render_pdf
from ..i18n import tr
from ..search import SearchFilters, find_assets
from .asset_dialog import AssetDialog
from .common import set_row, setup_table

COLUMNS = ["code", "item", "serial_placeholder", "brand", "department", "location", "qty", "notes"]


class SearchPanel(QWidget):
    def __init__(self, conn: sqlite3.Connection, lang: str = "ar", parent=None):
        super().__init__(parent)
        self.conn, self.lang = conn, lang
        self.current_rows = []
        self._build()
        self.run_search()

    # ---------------------------------------------------------------- UI ---
    def _build(self) -> None:
        self.setLayoutDirection(
            Qt.LayoutDirection.RightToLeft if self.lang == "ar" else Qt.LayoutDirection.LeftToRight
        )
        root = QVBoxLayout(self)

        filters = QGroupBox()
        frow = QHBoxLayout(filters)
        self.section_buttons: dict[str, QPushButton] = {}
        group = QButtonGroup(self)
        group.setExclusive(True)
        for key in ("all", "devices", "furniture", "electrical", "network"):
            btn = QPushButton(tr(key, self.lang))
            btn.setCheckable(True)
            btn.setChecked(key == "all")
            group.addButton(btn)
            self.section_buttons[key] = btn
            frow.addWidget(btn)
        group.buttonClicked.connect(self.run_search)

        self.combo_dept = QComboBox()
        self.combo_loc = QComboBox()
        self.combo_cat = QComboBox()
        for combo in (self.combo_dept, self.combo_loc, self.combo_cat):
            combo.setMinimumWidth(140)
            frow.addWidget(combo)
        self.edit_text = QLineEdit()
        self.edit_text.setPlaceholderText(tr("search_placeholder", self.lang))
        self.edit_serial = QLineEdit()
        self.edit_serial.setPlaceholderText(tr("serial_placeholder", self.lang))
        self.edit_text.returnPressed.connect(self.run_search)
        self.edit_serial.returnPressed.connect(self.run_search)
        frow.addWidget(self.edit_text)
        frow.addWidget(self.edit_serial)
        self.check_issues = QCheckBox(tr("unresolved", self.lang))
        frow.addWidget(self.check_issues)

        self.btn_search = QPushButton(tr("search", self.lang))
        self.btn_search.clicked.connect(self.run_search)
        self.btn_clear = QPushButton(tr("clear", self.lang))
        self.btn_clear.clicked.connect(self.clear_filters)
        frow.addWidget(self.btn_search)
        frow.addWidget(self.btn_clear)
        root.addWidget(filters)

        self.table = QTableWidget()
        setup_table(self.table, [tr(c, self.lang) for c in COLUMNS])
        self.table.doubleClicked.connect(self.open_details)
        root.addWidget(self.table, stretch=1)

        bottom = QHBoxLayout()
        self.lbl_count = QLabel()
        bottom.addWidget(self.lbl_count)
        bottom.addStretch()
        self.btn_excel = QPushButton(tr("export_excel", self.lang))
        self.btn_excel.clicked.connect(self.export_excel)
        self.btn_pdf = QPushButton(tr("export_pdf", self.lang))
        self.btn_pdf.clicked.connect(lambda: self.export_pdf(False))
        self.btn_print = QPushButton(tr("print", self.lang))
        self.btn_print.clicked.connect(lambda: self.export_pdf(True))
        for btn in (self.btn_excel, self.btn_pdf, self.btn_print):
            bottom.addWidget(btn)
        root.addLayout(bottom)

        for combo, table in (
            (self.combo_dept, "departments"),
            (self.combo_loc, "locations"),
            (self.combo_cat, "categories"),
        ):
            combo.addItem(tr("all", self.lang), None)
            for r in self.conn.execute(f"SELECT id, name_ar FROM {table} ORDER BY name_ar"):
                combo.addItem(r["name_ar"], r["id"])

    # ------------------------------------------------------------ actions ---
    def _selected_section(self) -> str:
        for key, btn in self.section_buttons.items():
            if btn.isChecked():
                return "" if key == "all" else key
        return ""

    def _filters(self) -> SearchFilters:
        return SearchFilters(
            section=self._selected_section(),
            department_id=self.combo_dept.currentData(),
            location_id=self.combo_loc.currentData(),
            category_id=self.combo_cat.currentData(),
            text=self.edit_text.text(),
            serial=self.edit_serial.text(),
            issues_only=self.check_issues.isChecked(),
        )

    def run_search(self) -> None:
        self.current_rows = find_assets(self.conn, self._filters())
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.current_rows))
        for i, r in enumerate(self.current_rows):
            set_row(self.table, i, [
                r["asset_code"], r["name_ar"], r["serial_number"], r["brand_model"],
                r["dept_ar"] or r["loc_ar"] or "", r["loc_ar"] or "",
                r["quantity"], r["notes"],
            ])
        self.table.setSortingEnabled(True)
        self.lbl_count.setText(f"{tr('results', self.lang)}: {len(self.current_rows)}")

    def clear_filters(self) -> None:
        self.section_buttons["all"].setChecked(True)
        for combo in (self.combo_dept, self.combo_loc, self.combo_cat):
            combo.setCurrentIndex(0)
        self.edit_text.clear()
        self.edit_serial.clear()
        self.check_issues.setChecked(False)
        self.run_search()

    def open_details(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        row = items[0].row()
        asset_id = self.current_rows[row]["id"]
        AssetDialog(self.conn, asset_id, self.lang, self).exec()

    def export_excel(self) -> None:
        if not self.current_rows:
            QMessageBox.information(self, tr("app_title", self.lang), tr("no_results", self.lang))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("export_excel", self.lang), "inventory_export.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        try:
            export_excel(self.current_rows, path)
            QMessageBox.information(self, tr("saved", self.lang), path)
        except Exception as exc:  # pragma: no cover - GUI feedback
            QMessageBox.critical(self, tr("error", self.lang), str(exc))

    def export_pdf(self, print_it: bool = False) -> None:
        if not self.current_rows:
            QMessageBox.information(self, tr("app_title", self.lang), tr("no_results", self.lang))
            return
        if print_it:
            from PySide6.QtGui import QTextDocument
            from PySide6.QtPrintSupport import QPrinter, QPrintDialog

            from ..exporter import build_report_html

            doc = QTextDocument()
            doc.setHtml(build_report_html(self.current_rows, "department", self.lang))
            printer = QPrinter()
            printer.setResolution(300)
            dialog = QPrintDialog(printer, self)
            if dialog.exec():
                doc.print_(printer)
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("export_pdf", self.lang), "inventory_report.pdf", "PDF (*.pdf)"
        )
        if not path:
            return
        try:
            render_pdf(self.current_rows, Path(path), "department", self.lang)
            QMessageBox.information(self, tr("saved", self.lang), path)
        except Exception as exc:  # pragma: no cover - GUI feedback
            QMessageBox.critical(self, tr("error", self.lang), str(exc))
