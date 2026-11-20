"""Capture real screenshots of each application tab (offscreen Qt)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app.db import connect
from app.ui.asset_dialog import AssetDialog
from app.ui.main_window import MainWindow

OUT = Path(__file__).resolve().parent.parent / "screenshots"
OUT.mkdir(exist_ok=True)

STYLE = """
QMainWindow, QWidget { background:#f4f7fa; }
QGroupBox { border:1px solid #d6e0ea; border-radius:6px; margin-top:8px; background:white; }
QGroupBox::title { subcontrol-origin:margin; padding:0 6px; color:#2f6da3; font-weight:bold; }
QPushButton { background:#2f6da3; color:white; border-radius:5px; padding:7px 14px; }
QPushButton:hover { background:#245980; }
QPushButton:checked { background:#1c4c70; }
QLineEdit, QComboBox { border:1px solid #c7d3df; border-radius:4px; padding:6px; background:white; }
QTableWidget { background:white; gridline-color:#dde5ed; alternate-background-color:#f6f9fc;
               selection-background-color:#d7e8f7; }
QHeaderView::section { background:#e8eef5; padding:5px; border:1px solid #d6e0ea; font-weight:bold; }
QTabWidget::pane { border:1px solid #d6e0ea; background:white; }
QTabBar::tab { background:#e8eef5; padding:8px 18px; border:1px solid #d6e0ea; }
QTabBar::tab:selected { background:#2f6da3; color:white; }
QLabel { color:#223344; }
"""


def main() -> None:
    app = QApplication(sys.argv)
    app.setFont(QFont("Noto Sans Arabic", 10))
    app.setStyleSheet(STYLE)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    conn = connect()
    window = MainWindow(conn, "ar")
    window.resize(1400, 860)
    window.show()
    app.processEvents()

    names = ["01_dashboard", "02_search", "03_import", "04_issues"]
    for i, name in enumerate(names):
        window.tabs.setCurrentIndex(i)
        app.processEvents()
        window.grab().save(str(OUT / f"{name}.png"))
        print("saved", name)

    # Search results filtered by serial and one asset detail dialog.
    panel = window.panels["search"]
    window.tabs.setCurrentIndex(1)
    panel.edit_serial.setText("PC29SJNE")
    panel.run_search()
    app.processEvents()
    window.grab().save(str(OUT / "05_search_serial.png"))
    print("saved 05_search_serial")

    dialog = AssetDialog(conn, panel.current_rows[0]["id"], "ar", window)
    dialog.show()
    app.processEvents()
    dialog.grab().save(str(OUT / "06_asset_details.png"))
    print("saved 06_asset_details")


if __name__ == "__main__":
    main()
