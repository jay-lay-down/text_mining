from __future__ import annotations

import traceback
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
    QMessageBox,
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
        self.analyzer = QComboBox()
        self.analyzer.addItems(["Kiwi (정밀)", "간단 토큰(한글만)"])
        self.pos_mode = QComboBox()
        self.pos_mode.addItems(["noun", "noun+adj+verb"])
        self.stopwords_edit = QTextEdit()
        self.custom_drop_edit = QTextEdit()
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

        self.wordcloud_label = QLabel("")
        self.wordcloud_label.setMinimumHeight(240)
        self.status_strip = StatusStrip()
        self.empty_warning = QLabel("")
        self._is_running = False
        self.miner = kiwi_tm.KiwiTextMiner()
        self._build_ui()

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "텍스트마이닝 오류", message)

    def _build_ui(self) -> None:
        form = QFormLayout()
        form.addRow("텍스트 소스", self.text_source)
        form.addRow("토크나이저", self.analyzer)
        form.addRow("품사", self.pos_mode)
        form.addRow("최소 빈도", self.min_freq)
        form.addRow("최소 글자수", self.token_min_len)

        sw_box = QGroupBox("불용어 (줄바꿈)")
        sw_layout = QVBoxLayout()
        self.stopwords_edit.setFixedHeight(60)
        sw_layout.addWidget(self.stopwords_edit)
        sw_box.setLayout(sw_layout)

        drop_box = QGroupBox("추가 제거 토큰(줄바꿈)")
        drop_layout = QVBoxLayout()
        self.custom_drop_edit.setFixedHeight(60)
        drop_layout.addWidget(self.custom_drop_edit)
        drop_box.setLayout(drop_layout)

        clean_box = QGroupBox("전처리 옵션")
        opt_grid = QGridLayout()
        opt_grid.setHorizontalSpacing(14)
        opt_grid.setVerticalSpacing(10)
        opts = list(self.clean_opts.values())
        for idx, opt in enumerate(opts):
            opt_grid.addWidget(opt, idx // 3, idx % 3)
        # place number/english toggles on their own row to avoid crowding
        row_for_misc = (len(opts) + 2) // 3
        opt_grid.addWidget(self.keep_number, row_for_misc, 0)
        opt_grid.addWidget(self.keep_english, row_for_misc, 1)
        opt_grid.setColumnStretch(0, 1)
        opt_grid.setColumnStretch(1, 1)
        opt_grid.setColumnStretch(2, 1)
        clean_box.setLayout(opt_grid)

        controls = QHBoxLayout()
        self.run_btn = QPushButton("실행")
        self.run_btn.clicked.connect(self.run_textmining)
        controls.addWidget(self.empty_warning)
        controls.addStretch()
        controls.addWidget(self.run_btn)

        top_grid = QGridLayout()
        top_grid.addWidget(clean_box, 0, 0)
        top_grid.addWidget(sw_box, 0, 1)
        top_grid.addWidget(drop_box, 0, 2)
        top_grid.addLayout(form, 1, 0, 1, 3)
        top_grid.addLayout(controls, 2, 0, 1, 2)

        results_row = QHBoxLayout()
        left_col = QVBoxLayout()
        left_col.addWidget(QLabel("Top 50"))
        left_col.addWidget(self.top50_table)
        left_col.addWidget(QLabel("월별 Top"))
        left_col.addWidget(self.monthly_table)
        right_col = QVBoxLayout()
        right_col.addWidget(QLabel("전체 빈도"))
        right_col.addWidget(self.freq_table)
        wc_box = QVBoxLayout()
        wc_box.addWidget(QLabel("워드클라우드"))
        wc_box.addWidget(self.wordcloud_label)
        right_col.addLayout(wc_box)
        results_row.addLayout(left_col, 1)
        results_row.addLayout(right_col, 1)

        layout = QVBoxLayout()
        layout.addLayout(top_grid)
        layout.addLayout(results_row)
        layout.addWidget(self.status_strip)
        layout.addStretch()
        self.setLayout(layout)

    def run_textmining(self) -> None:
        if self._is_running:
            return
        if self.app_state.dedup_df is None or self.app_state.dedup_df.empty:
            self._show_error("분석할 데이터가 없습니다. 전처리 후 다시 시도하세요.")
            return
        self._is_running = True
        self.run_btn.setEnabled(False)
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
            "custom_drop": self.custom_drop_edit.toPlainText(),
            "min_freq": int(self.min_freq.currentText()),
            "min_length": int(self.token_min_len.currentText()),
            "strict_korean_only": self.clean_opts["strict_korean_only"].isChecked(),
            "token_min_len": int(self.token_min_len.currentText()),
            "analyzer": "simple" if self.analyzer.currentIndex() == 1 else "kiwi",
        }
        try:
            tokens_df, freq_df, top50_df, monthly_df, audit_df, empty_df = self.miner.build_tokens(
                self.app_state.dedup_df, options, text_source=self.text_source.currentText()
            )
        except Exception as exc:  # noqa: BLE001
            detail = traceback.format_exc()
            self._show_error(f"텍스트마이닝 중 오류가 발생했습니다:\n{exc}\n\n{detail}")
            self.run_btn.setEnabled(True)
            self._is_running = False
            return
        if tokens_df.empty:
            self._show_error("토큰이 생성되지 않았습니다. 옵션을 완화하거나 데이터 준비 단계를 확인하세요.")
            self.run_btn.setEnabled(True)
            self._is_running = False
            return
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
            try:
                font_to_use = str(font_path) if font_path.exists() else None
                if font_to_use is None:
                    font_to_use = str(wc.resource_path("assets/fonts/NanumGothic.ttf"))
                wc.generate_wordcloud(tokens_flat, font_to_use, output_path)
                self.wordcloud_label.setText("")
                pixmap = QPixmap(str(output_path))
                self.wordcloud_label.setPixmap(pixmap)
            except Exception as exc:  # noqa: BLE001
                detail = traceback.format_exc()
                self.wordcloud_label.setText(f"워드클라우드 생성 실패: {exc}")
                self._show_error(f"워드클라우드 생성 실패: {exc}\n\n{detail}")
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
        self.run_btn.setEnabled(True)
        self._is_running = False
