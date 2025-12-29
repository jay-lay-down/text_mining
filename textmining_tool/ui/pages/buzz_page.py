from __future__ import annotations

import pandas as pd
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ...core import pivot
from ...core.state import AppState
from ..widgets import PandasModel, StatusStrip


class BuzzPage(QWidget):
    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.period_combo = QComboBox()
        self.period_combo.addItems(["year", "half", "quarter", "month", "week", "day", "hour"])
        self.include_page_type = QCheckBox("page_type별 보기")
        self.pivot_model = PandasModel(pd.DataFrame())
        self.pivot_table = QTableView()
        self.pivot_table.setModel(self.pivot_model)
        self.status_strip = StatusStrip()
        self._build_ui()

    def _build_ui(self) -> None:
        config_box = QGroupBox("버즈 피벗")
        cfg_layout = QHBoxLayout()
        cfg_layout.addWidget(QLabel("기간 단위"))
        cfg_layout.addWidget(self.period_combo)
        cfg_layout.addWidget(self.include_page_type)
        btn = QPushButton("피벗 생성")
        btn.clicked.connect(self.generate_pivot)
        cfg_layout.addWidget(btn)
        cfg_layout.addStretch()
        config_box.setLayout(cfg_layout)

        layout = QVBoxLayout()
        layout.addWidget(config_box)
        layout.addWidget(self.pivot_table)
        layout.addWidget(self.status_strip)
        layout.addStretch()
        self.setLayout(layout)

    def generate_pivot(self) -> None:
        if self.app_state.dedup_df is None:
            return
        unit = self.period_combo.currentText()
        self.app_state.period_unit = unit
        self.app_state.pivot_df = pivot.build_pivot(
            self.app_state.dedup_df,
            unit,
            self.include_page_type.isChecked(),
            dt_col=self.app_state.date_col,
        )
        self.pivot_model.update(self.app_state.pivot_df)
        rows = len(self.app_state.dedup_df)
        self.status_strip.update(rows, unit, self.app_state.runtime_options.get("news_excluded", False))
        self.app_state.update_log("pivot", "pivot generated", {"rows": len(self.app_state.pivot_df)})
