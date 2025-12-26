from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableView,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...core import kiwi_tm, wc
from ...core.state import AppState
from ..widgets import PandasModel, StatusStrip


class TextMiningPage(QWidget):
    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.clean_opts = {
            "korean_only": QCheckBox("한국어만"),
            "strict_korean_only": QCheckBox("순수 한글 단어만 사용(가-힣)"),
            "remove_laugh": QCheckBox("ㅋㅋ/ㅎㅎ/ㅠㅠ 제거"),
            "remove_emoji": QCheckBox("이모지 제거"),
            "remove_url": QCheckBox("URL 제거"),
            "remove_email": QCheckBox("이메일 제거"),
            "remove_hashtag": QCheckBox("해시태그 제거"),
            "remove_mention": QCheckBox("멘션 제거"),
            "strip_whitespace": QCheckBox("공백 정리"),
        }
        for key, opt in self.clean_opts.items():
            opt.setChecked(True)
        self.keep_number = QCheckBox("숫자 유지")
        self.keep_english = QCheckBox("영문 유지")
        self.min_freq = QComboBox()
        self.min_freq.addItems(["1", "2", "3", "5", "10"])
        self.text_source = QComboBox()
        self.text_source.addItems(["both", "title", "full"])
        self.pos_mode = QComboBox()
        self.pos_mode.addItems(["noun", "noun+adj+verb"])
        self.stopwords_edit = QTextEdit()
        self.token_min_len = QComboBox()
        self.token_min_len.addItems(["1", "2", "3", "4"])

        self.top50_model = PandasModel(pd.DataFrame())
        self.top50_table = QTableView()
        self.top50_table.setModel(self.top50_model)

        self.freq_model = PandasModel(pd.DataFrame())
        self.freq_table = QTableView()
        self.freq_table.setModel(self.freq_model)

        self.monthly_model = PandasModel(pd.DataFrame())
        self.monthly_table = QTableView()
        self.monthly_table.setModel(self.monthly_model)

        self.wordcloud_label = QLabel("워드클라우드")
        self.status_strip = StatusStrip()
        self.empty_warning = QLabel("")
        self._build_ui()

    def _build_ui(self) -> None:
        form = QFormLayout()
        form.addRow("텍스트 소스", self.text_source)
        form.addRow("품사", self.pos_mode)
        form.addRow("최소 빈도", self.min_freq)
        form.addRow("최소 글자수", self.token_min_len)

        sw_box = QGroupBox("불용어 (줄바꿈)")
        sw_layout = QVBoxLayout()
        sw_layout.addWidget(self.stopwords_edit)
        sw_box.setLayout(sw_layout)

        clean_box = QGroupBox("전처리 옵션")
        c_layout = QVBoxLayout()
        for opt in self.clean_opts.values():
            c_layout.addWidget(opt)
        c_layout.addWidget(self.keep_number)
        c_layout.addWidget(self.keep_english)
        clean_box.setLayout(c_layout)

        controls = QHBoxLayout()
        self.run_btn = QPushButton("텍마 실행")
        self.run_btn.clicked.connect(self.run_textmining)
        controls.addWidget(self.empty_warning)
        controls.addStretch()
        controls.addWidget(self.run_btn)

        top_grid = QGridLayout()
        top_grid.addWidget(clean_box, 0, 0)
        top_grid.addWidget(sw_box, 0, 1)
        top_grid.addLayout(form, 1, 0, 1, 2)
        top_grid.addLayout(controls, 2, 0, 1, 2)

        layout = QVBoxLayout()
        layout.addLayout(top_grid)
        layout.addWidget(QLabel("Top 50"))
        layout.addWidget(self.top50_table)
        layout.addWidget(QLabel("전체 빈도"))
        layout.addWidget(self.freq_table)
        layout.addWidget(QLabel("월별 Top"))
        layout.addWidget(self.monthly_table)
        layout.addWidget(self.wordcloud_label)
        layout.addWidget(self.status_strip)
        layout.addStretch()
        self.setLayout(layout)

    def run_textmining(self) -> None:
        if self.app_state.dedup_df is None:
            return
        miner = kiwi_tm.KiwiTextMiner()
        options = {
            "korean_only": self.clean_opts["korean_only"].isChecked(),
            "remove_url": self.clean_opts["remove_url"].isChecked(),
            "remove_email": self.clean_opts["remove_email"].isChecked(),
            "remove_hashtag": self.clean_opts["remove_hashtag"].isChecked(),
            "remove_mention": self.clean_opts["remove_mention"].isChecked(),
            "strip_whitespace": self.clean_opts["strip_whitespace"].isChecked(),
            "keep_number": self.keep_number.isChecked(),
            "keep_english": self.keep_english.isChecked(),
            "pos": "noun" if self.pos_mode.currentText() == "noun" else "noun+adj+verb",
            "stopwords": self.stopwords_edit.toPlainText(),
            "min_freq": int(self.min_freq.currentText()),
            "min_length": int(self.token_min_len.currentText()),
            "strict_korean_only": self.clean_opts["strict_korean_only"].isChecked(),
            "token_min_len": int(self.token_min_len.currentText()),
        }
        tokens_df, freq_df, top50_df, monthly_df, audit_df, empty_df = miner.build_tokens(
            self.app_state.dedup_df, options, text_source=self.text_source.currentText()
        )
        self.app_state.tokens_df = tokens_df
        self.app_state.freq_df = freq_df
        self.app_state.top50_df = top50_df
        self.app_state.monthly_top_df = monthly_df
        self.app_state.audit_report_df = audit_df
        self.app_state.empty_doc_report_df = empty_df
        self.top50_model.update(top50_df)
        self.freq_model.update(freq_df)
        self.monthly_model.update(monthly_df)
        tokens_flat = []
        if not tokens_df.empty and "tokens" in tokens_df.columns:
            for token_list in tokens_df["tokens"]:
                tokens_flat.extend(token_list)
        assets_dir = Path(__file__).resolve().parents[2] / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        font_path = assets_dir / "fonts" / "NanumGothic.ttf"
        output_path = assets_dir / "wordcloud.png"
        if tokens_flat:
            wc.generate_wordcloud(tokens_flat, str(font_path), output_path)
            self.wordcloud_label.setText("")
            pixmap = QPixmap(str(output_path))
            self.wordcloud_label.setPixmap(pixmap)
        else:
            self.wordcloud_label.setText("토큰 없음")
        total_docs = len(self.app_state.dedup_df) if self.app_state.dedup_df is not None else 0
        if self.app_state.empty_doc_report_df is not None and not self.app_state.empty_doc_report_df.empty:
            empty_clean = len(self.app_state.empty_doc_report_df[self.app_state.empty_doc_report_df["empty_clean"]])
            empty_token = len(self.app_state.empty_doc_report_df[self.app_state.empty_doc_report_df["empty_token"]])
        else:
            empty_clean = 0
            empty_token = 0
        warn_text = f"빈 문서(클린): {empty_clean}/{total_docs}, 빈 문서(토큰): {empty_token}/{total_docs}"
        self.empty_warning.setText(warn_text)
        self.status_strip.update(len(tokens_df), self.app_state.period_unit, self.app_state.runtime_options.get("news_excluded", False))
        self.app_state.update_log("textmining", "completed", {"tokens": len(freq_df)})
