"""Main window hosting the five tabs and the Arabic/English switch."""
from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QTabWidget

from ..i18n import tr
from .dashboard import Dashboard
from .import_panel import ImportPanel
from .issues_panel import IssuesPanel
from .search_panel import SearchPanel


class MainWindow(QMainWindow):
    def __init__(self, conn: sqlite3.Connection, lang: str = "ar"):
        super().__init__()
        self.conn, self.lang = conn, lang
        self.setWindowTitle(tr("app_title", lang))
        self.resize(1180, 720)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if lang == "ar" else Qt.LayoutDirection.LeftToRight)
        self._build()

    def _build(self) -> None:
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.panels = {}
        self._fill_tabs()

        bar = self.menuBar()
        self.lang_action = QAction("English" if self.lang == "ar" else "العربية", self)
        self.lang_action.triggered.connect(self.toggle_language)
        bar.addAction(self.lang_action)

    def _fill_tabs(self) -> None:
        self.tabs.clear()
        self.panels = {
            "dashboard": Dashboard(self.conn, self.lang),
            "search": SearchPanel(self.conn, self.lang),
            "import": ImportPanel(self.conn, self.lang),
            "issues": IssuesPanel(self.conn, self.lang),
        }
        self.panels["import"].imported.connect(self.refresh_all)
        self.panels["issues"].changed.connect(self.refresh_all)
        for key in ("dashboard", "search", "import", "issues"):
            self.tabs.addTab(self.panels[key], tr("tab_" + key, self.lang))

    def refresh_all(self) -> None:
        for panel in (self.panels.get("dashboard"), self.panels.get("search")):
            if panel and hasattr(panel, "refresh"):
                panel.refresh()
        if self.panels.get("search"):
            self.panels["search"].run_search()

    def toggle_language(self) -> None:
        self.lang = "en" if self.lang == "ar" else "ar"
        self.setWindowTitle(tr("app_title", self.lang))
        self.setLayoutDirection(
            Qt.LayoutDirection.RightToLeft if self.lang == "ar" else Qt.LayoutDirection.LeftToRight
        )
        self.lang_action.setText("English" if self.lang == "ar" else "العربية")
        self._fill_tabs()
