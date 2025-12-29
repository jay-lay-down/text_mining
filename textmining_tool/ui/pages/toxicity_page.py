from __future__ import annotations

import pandas as pd
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableView,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...core import toxicity
from ...core.state import AppState
from ..widgets import PandasModel, StatusStrip


class ToxicityPage(QWidget):
    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.text_mode = QComboBox()
        self.text_mode.addItems(["clean_text", "Full Text", "both"])
        self.context_mode = QComboBox()
        self.context_mode.addItems(["CONTEXT_AWARE", "ALWAYS_PENALIZE"])
        self.role_delta_inputs = {
            "EMPHASIS_POS": QComboBox(),
            "GENERAL_EXPLETIVE": QComboBox(),
            "EMPHASIS_NEG": QComboBox(),
            "TARGETED_INSULT": QComboBox(),
            "SLUR_HATE": QComboBox(),
        }
        for combo in self.role_delta_inputs.values():
            combo.addItems(["-2", "-1", "0", "1"])
        def _mini_textbox(default: str = "") -> QTextEdit:
            box = QTextEdit(default)
            box.setMinimumHeight(64)
            return box

        self.profanity_tokens = _mini_textbox("\n".join(toxicity.DEFAULT_DICTS["PROFANITY_TOKENS"]))
        self.pos_cues = _mini_textbox("\n".join(toxicity.DEFAULT_DICTS["POS_CUES"]))
        self.neg_cues = _mini_textbox("\n".join(toxicity.DEFAULT_DICTS["NEG_CUES"]))
        self.target_cues = _mini_textbox("\n".join(toxicity.DEFAULT_DICTS["TARGET_CUES"]))
        self.insult_suffix = _mini_textbox("\n".join(toxicity.DEFAULT_DICTS["INSULT_SUFFIX"]))
        self.whitelist = _mini_textbox()

        self.table_model = PandasModel(pd.DataFrame())
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.summary_model = PandasModel(pd.DataFrame())
        self.summary_view = QTableView()
        self.summary_view.setModel(self.summary_model)
        self.status_strip = StatusStrip()
        self._build_ui()

    def _build_ui(self) -> None:
        form = QFormLayout()
        form.setVerticalSpacing(6)
        form.addRow("텍스트 모드", self.text_mode)
        form.addRow("Context 모드", self.context_mode)
        for role, combo in self.role_delta_inputs.items():
            form.addRow(f"{role} delta", combo)
        form_box = QGroupBox("역할/감점 설정")
        form_box.setLayout(form)

        dict_box = QGroupBox("사전 편집")
        dict_layout = QVBoxLayout()
        dict_layout.addWidget(QLabel("PROFANITY_TOKENS"))
        dict_layout.addWidget(self.profanity_tokens)
        dict_layout.addWidget(QLabel("POS_CUES"))
        dict_layout.addWidget(self.pos_cues)
        dict_layout.addWidget(QLabel("NEG_CUES"))
        dict_layout.addWidget(self.neg_cues)
        dict_layout.addWidget(QLabel("TARGET_CUES"))
        dict_layout.addWidget(self.target_cues)
        dict_layout.addWidget(QLabel("INSULT_SUFFIX"))
        dict_layout.addWidget(self.insult_suffix)
        dict_layout.addWidget(QLabel("화이트리스트 패턴"))
        dict_layout.addWidget(self.whitelist)
        dict_box.setLayout(dict_layout)
        dict_box.setMinimumWidth(700)

        run_btn = QPushButton("유해성 스캔 실행")
        run_btn.clicked.connect(self.run_scan)
        run_row = QHBoxLayout()
        run_row.addStretch()
        run_row.addWidget(run_btn)

        top_grid = QGridLayout()
        top_grid.addWidget(form_box, 0, 0)
        top_grid.addWidget(dict_box, 0, 1)
        top_grid.addLayout(run_row, 1, 0, 1, 2)
        top_grid.setColumnStretch(0, 1)
        top_grid.setColumnStretch(1, 3)

        layout = QVBoxLayout()
        layout.addLayout(top_grid)
        layout.addWidget(QLabel("상세"))
        layout.addWidget(self.table_view)
        layout.addWidget(QLabel("요약"))
        layout.addWidget(self.summary_view)
        layout.addWidget(self.status_strip)
        layout.addStretch()
        self.setLayout(layout)

    def run_scan(self) -> None:
        if (self.app_state.tokens_df is None or self.app_state.tokens_df.empty) and (
            self.app_state.dedup_df is None or self.app_state.dedup_df.empty
        ):
            QMessageBox.warning(self, "유해성 스캔", "분석할 데이터가 없습니다. 전처리/텍스트마이닝을 먼저 실행하세요.")
            return
        try:
            dictionaries = {
                "PROFANITY_TOKENS": [l.strip() for l in self.profanity_tokens.toPlainText().splitlines() if l.strip()],
                "POS_CUES": [l.strip() for l in self.pos_cues.toPlainText().splitlines() if l.strip()],
                "NEG_CUES": [l.strip() for l in self.neg_cues.toPlainText().splitlines() if l.strip()],
                "TARGET_CUES": [l.strip() for l in self.target_cues.toPlainText().splitlines() if l.strip()],
                "INSULT_SUFFIX": [l.strip() for l in self.insult_suffix.toPlainText().splitlines() if l.strip()],
                "SLUR_HATE": toxicity.DEFAULT_DICTS.get("SLUR_HATE", []),
                "EMO_POS": toxicity.DEFAULT_DICTS.get("EMO_POS", []),
            }
            role_to_delta = {role: int(combo.currentText()) for role, combo in self.role_delta_inputs.items()}
            whitelist = [l.strip() for l in self.whitelist.toPlainText().splitlines() if l.strip()]
            text_col = "clean_text" if self.text_mode.currentText() == "clean_text" else "Full Text"
            target_df = self.app_state.tokens_df if self.app_state.tokens_df is not None else self.app_state.dedup_df
            detail_df, summary_df = toxicity.scan_dataframe(
                target_df,
                text_col=text_col,
                dictionaries=dictionaries,
                whitelist=whitelist,
                context_mode=self.context_mode.currentText(),
                role_to_delta=role_to_delta,
            )
            self.app_state.toxicity_detail_df = detail_df
            self.app_state.toxicity_summary_df = summary_df
            self.table_model.update(detail_df)
            self.summary_model.update(summary_df)
            rows = len(detail_df)
            self.status_strip.update(rows, self.app_state.period_unit, self.app_state.runtime_options.get("news_excluded", False))
            self.app_state.update_log("toxicity", "completed", {"rows": rows})
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "유해성 스캔 오류", f"유해성 스캔 중 오류가 발생했습니다: {exc}")
