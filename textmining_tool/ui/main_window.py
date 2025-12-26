from __future__ import annotations

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget

from ..core.state import AppState, DEFAULT_EXPORT_SHEETS
from .pages.buzz_page import BuzzPage
from .pages.export_page import ExportPage
from .pages.network_page import NetworkPage
from .pages.preprocess_page import PreprocessPage
from .pages.sentiment_page import SentimentPage
from .pages.toxicity_page import ToxicityPage
from .pages.textmining_page import TextMiningPage


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
        self._init_pages()
        container = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.tab)
        container.setLayout(layout)
        self.setCentralWidget(container)

    def _init_pages(self) -> None:
        pages = [
            ("데이터 준비", PreprocessPage(self.app_state)),
            ("트렌드/피벗", BuzzPage(self.app_state)),
            ("키워드·토픽", TextMiningPage(self.app_state)),
            ("유해성/맥락", ToxicityPage(self.app_state)),
            ("감성/증거", SentimentPage(self.app_state)),
            ("연관/네트워크", NetworkPage(self.app_state)),
            ("내보내기", ExportPage(self.app_state)),
        ]
        for name, widget in pages:
            self.tab.addTab(widget, name)
