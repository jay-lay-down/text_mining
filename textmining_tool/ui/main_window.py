from __future__ import annotations

from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

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
        self.menu = QListWidget()
        self.stack = QStackedWidget()
        self._init_pages()
        container = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.menu)
        layout.addWidget(self.stack)
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.menu.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.menu.setCurrentRow(0)

    def _init_pages(self) -> None:
        pages = [
            ("전처리", PreprocessPage(self.app_state)),
            ("버즈", BuzzPage(self.app_state)),
            ("텍마", TextMiningPage(self.app_state)),
            ("유해성", ToxicityPage(self.app_state)),
            ("감성", SentimentPage(self.app_state)),
            ("네트워크", NetworkPage(self.app_state)),
            ("Export", ExportPage(self.app_state)),
        ]
        for name, widget in pages:
            item = QListWidgetItem(name)
            self.menu.addItem(item)
            self.stack.addWidget(widget)
