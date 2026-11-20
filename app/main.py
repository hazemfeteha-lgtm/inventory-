"""Application entry point (also the PyInstaller build target)."""
from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from .db import connect, init_db
from .ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    app.setApplicationName("Egypt Services Center Inventory")
    conn = connect()
    init_db(conn)
    window = MainWindow(conn)
    window.show()
    result = app.exec()
    conn.close()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
