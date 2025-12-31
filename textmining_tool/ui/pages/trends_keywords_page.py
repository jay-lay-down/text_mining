from __future__ import annotations

from PyQt6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from .buzz_page import BuzzPage
from .textmining_page import TextMiningPage
from ...core.state import AppState


class TrendsKeywordsPage(QWidget):
    """Combined page that hosts Trends/Pivot and Topics/Wordcloud under one top-level tab."""

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.buzz_page = BuzzPage(app_state, self)
        self.text_page = TextMiningPage(app_state, self)
        self._build_ui()

    def _build_ui(self) -> None:
        tabs = QTabWidget()
        tabs.addTab(self.buzz_page, "Trends / Pivot")
        tabs.addTab(self.text_page, "Topics / Wordcloud")

        layout = QVBoxLayout()
        layout.addWidget(tabs)
        self.setLayout(layout)
