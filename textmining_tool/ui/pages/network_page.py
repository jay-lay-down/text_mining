from __future__ import annotations

from pathlib import Path

import pandas as pd
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ...core import association, network
from ...core.state import AppState
from ..widgets import PandasModel, StatusStrip


class NetworkPage(QWidget):
    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Apriori", "Network"])
        self.min_support = QDoubleSpinBox()
        self.min_support.setRange(0.0, 1.0)
        self.min_support.setValue(0.05)
        self.min_conf = QDoubleSpinBox()
        self.min_conf.setRange(0.0, 1.0)
        self.min_conf.setValue(0.3)
        self.min_lift = QDoubleSpinBox()
        self.min_lift.setRange(0.0, 10.0)
        self.min_lift.setValue(1.0)
        self.min_edge = QSpinBox()
        self.min_edge.setRange(1, 100)
        self.min_edge.setValue(2)

        self.rules_model = PandasModel(pd.DataFrame())
        self.rules_table = QTableView()
        self.rules_table.setModel(self.rules_model)

        self.nodes_model = PandasModel(pd.DataFrame())
        self.nodes_table = QTableView()
        self.nodes_table.setModel(self.nodes_model)

        self.edges_model = PandasModel(pd.DataFrame())
        self.edges_table = QTableView()
        self.edges_table.setModel(self.edges_model)

        self.web_view = QWebEngineView()
        self.status_strip = StatusStrip()
        self._build_ui()

    def _build_ui(self) -> None:
        form = QFormLayout()
        form.addRow("모드", self.mode_combo)
        form.addRow("min_support", self.min_support)
        form.addRow("min_confidence", self.min_conf)
        form.addRow("min_lift", self.min_lift)
        form.addRow("min_edge_weight", self.min_edge)
        cfg_box = QGroupBox("연관/네트워크")
        cfg_box.setLayout(form)

        btn = QPushButton("실행")
        btn.clicked.connect(self.run_analysis)

        layout = QVBoxLayout()
        layout.addWidget(cfg_box)
        layout.addWidget(btn)
        layout.addWidget(QLabel("Rules"))
        layout.addWidget(self.rules_table)
        layout.addWidget(QLabel("Nodes"))
        layout.addWidget(self.nodes_table)
        layout.addWidget(QLabel("Edges"))
        layout.addWidget(self.edges_table)
        layout.addWidget(self.web_view)
        layout.addWidget(self.status_strip)
        layout.addStretch()
        self.setLayout(layout)

    def run_analysis(self) -> None:
        if self.app_state.tokens_df is None:
            return
        token_sets = self.app_state.tokens_df["tokens"].tolist()
        if self.mode_combo.currentText() == "Apriori":
            rules_df = association.apriori_rules(token_sets, self.min_support.value(), self.min_conf.value(), self.min_lift.value())
            self.app_state.rules_df = rules_df
            self.rules_model.update(rules_df)
        else:
            nodes_df, edges_df = network.build_cooccurrence_network(token_sets, self.min_edge.value())
            self.app_state.nodes_df = nodes_df
            self.app_state.edges_df = edges_df
            self.nodes_model.update(nodes_df)
            self.edges_model.update(edges_df)
            if not nodes_df.empty:
                assets_dir = Path(__file__).resolve().parents[2] / "assets"
                assets_dir.mkdir(parents=True, exist_ok=True)
                html_path = assets_dir / "network.html"
                network.render_pyvis_html(nodes_df, edges_df, html_path)
                self.app_state.pyvis_html_path = html_path
                from PyQt6.QtCore import QUrl

                self.web_view.setUrl(QUrl.fromLocalFile(str(html_path)))
        rows = len(self.app_state.dedup_df) if self.app_state.dedup_df is not None else 0
        self.status_strip.update(rows, self.app_state.period_unit, self.app_state.runtime_options.get("news_excluded", False))
        self.app_state.update_log("network", "completed")
