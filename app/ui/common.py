"""Small reusable Qt helpers."""
from __future__ import annotations

from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget


def setup_table(table: QTableWidget, headers: list[str]) -> None:
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.verticalHeader().hide()
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    table.horizontalHeader().setStretchLastSection(True)
    table.setSortingEnabled(True)


def set_row(table: QTableWidget, index: int, values: list[object]) -> None:
    from PySide6.QtWidgets import QTableWidgetItem

    for col, value in enumerate(values):
        item = QTableWidgetItem("" if value is None else str(value))
        table.setItem(index, col, item)
