from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...core.exporter import SHEET_MAPPING, export_selected_sheets
from ...core.state import AppState


class ExportPage(QWidget):
    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.checkboxes: dict[str, QCheckBox] = {}
        self.include_empty = QCheckBox("빈 시트라도 포함")
        self._build_ui()

    def _build_ui(self) -> None:
        grid = QGridLayout()
        for i, key in enumerate(SHEET_MAPPING.keys()):
            chk = QCheckBox(key)
            chk.setChecked(True)
            self.checkboxes[key] = chk
            grid.addWidget(chk, i // 2, i % 2)
        container = QWidget()
        container.setLayout(grid)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)

        btn_save = QPushButton("엑셀 생성")
        btn_save.clicked.connect(self.save_excel)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("저장할 시트 선택"))
        layout.addWidget(scroll)
        layout.addWidget(self.include_empty)
        layout.addWidget(btn_save)
        layout.addStretch()
        self.setLayout(layout)

    def save_excel(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "경로 선택", filter="Excel (*.xlsx)")
        if not path:
            return
        selected = [k for k, chk in self.checkboxes.items() if chk.isChecked()]
        export_selected_sheets(Path(path), self.app_state, selected, include_empty=self.include_empty.isChecked())
        self.app_state.update_log("export", "saved", {"path": path})
