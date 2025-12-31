from __future__ import annotations

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget

from ..core.state import AppState, DEFAULT_EXPORT_SHEETS
from .pages.buzz_page import BuzzPage
from .pages.export_page import ExportPage
from .pages.network_page import NetworkPage
from .pages.preprocess_page import PreprocessPage
from .pages.sentiment_page import SentimentPage
from .pages.textmining_page import TextMiningPage
from .pages.toxicity_page import ToxicityPage


class MainWindow(QMainWindow):
    def __init__(self, app_state: AppState | None = None) -> None:
        super().__init__()
        self.setWindowTitle("텍스트마이닝 AI 툴")
        self.resize(1400, 900)
        self.app_state = app_state or AppState()
        if not self.app_state.export_sheet_flags:
            self.app_state.export_sheet_flags = {k: True for k in DEFAULT_EXPORT_SHEETS}
        self.tab = QTabWidget()
        self.tab.setTabPosition(QTabWidget.TabPosition.North)
        self.tab.setStyleSheet(
            """
            QTabBar::tab {
                background: #e6f0ff;
                color: #1c2b4a;
                padding: 8px 14px;
                margin: 2px;
                border-radius: 6px;
            }
            QTabBar::tab:selected {
                background: #2f6df6;
                color: white;
                font-weight: 600;
            }
            QTabWidget::pane {
                border: 1px solid #2f6df6;
                border-radius: 8px;
            }
            """
        )
        self._init_pages()
        container = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.tab)
        container.setLayout(layout)
        self.setCentralWidget(container)

    def _init_pages(self) -> None:
        page_builders = [
            ("Data Prep", PreprocessPage),
            ("Trends", BuzzPage),
            ("Keywords", TextMiningPage),
            ("Toxicity / Context", ToxicityPage),
            ("Sentiment / Evidence", SentimentPage),
            ("Network", NetworkPage),
            ("Export", ExportPage),
        ]
        for name, page_cls in page_builders:
            try:
                widget = page_cls(self.app_state)
            except Exception as exc:  # noqa: BLE001
                from PyQt6.QtWidgets import QLabel

                widget = QLabel(f"{name} 초기화 오류: {exc}")
            self.tab.addTab(widget, name)
