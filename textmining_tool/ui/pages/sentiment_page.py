from __future__ import annotations

import pandas as pd
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableView,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...core import gemini_client, rules_engine, toxicity
from ...core.state import AppState
from ..widgets import PandasModel, StatusStrip
try:
    from kss import split_sentences
except Exception:  # noqa: BLE001
    def split_sentences(text: str) -> list[str]:
        import re
        return [s.strip() for s in re.split(r"[\\.\\?!\\n]", text) if s.strip()]


class SentimentPage(QWidget):
    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.profanity_mode = QComboBox()
        self.profanity_mode.addItems(["ONCE_FIXED", "COUNT_ACCUM", "COUNT_CAP_TO_2"])
        self.profanity_scope = QComboBox()
        self.profanity_scope.addItems(["CLEAN_TEXT_ONLY", "RAW_TEXT_ONLY", "BOTH"])
        self.profanity_delta = QComboBox()
        self.profanity_delta.addItems(["-1", "-2"])
        self.context_mode = QComboBox()
        self.context_mode.addItems(["CONTEXT_AWARE", "ALWAYS_PENALIZE"])
        self.profanity_list = QTextEdit()
        self.min_sentence_len = QComboBox()
        self.min_sentence_len.addItems(["3", "5", "8"])

        self.sentiment_model = PandasModel(pd.DataFrame())
        self.sentiment_table = QTableView()
        self.sentiment_table.setModel(self.sentiment_model)
        self.status_strip = StatusStrip()
        self._build_ui()

    def _build_ui(self) -> None:
        form = QFormLayout()
        form.addRow("Gemini API Key", self.api_key_edit)
        form.addRow("욕설 모드", self.profanity_mode)
        form.addRow("욕설 스코프", self.profanity_scope)
        form.addRow("욕설 패널티", self.profanity_delta)
        form.addRow("Context 모드", self.context_mode)
        form.addRow("최소 문장 길이", self.min_sentence_len)
        form.addRow("욕설 리스트", self.profanity_list)
        cfg_box = QGroupBox("감성 설정")
        cfg_box.setLayout(form)

        btn = QPushButton("실행")
        btn.clicked.connect(self.run_sentiment)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn)

        top_grid = QGridLayout()
        top_grid.addWidget(cfg_box, 0, 0)
        top_grid.addLayout(btn_row, 1, 0)

        layout = QVBoxLayout()
        layout.addLayout(top_grid)
        layout.addWidget(self.sentiment_table)
        layout.addWidget(self.status_strip)
        layout.addStretch()
        self.setLayout(layout)

    def run_sentiment(self) -> None:
        if self.app_state.tokens_df is None:
            return
        api_key = self.api_key_edit.text().strip()
        sentence_rows = []
        min_len = int(self.min_sentence_len.currentText())
        for _, row in self.app_state.tokens_df.iterrows():
            text = row.get("clean_text", "")
            sentences = [s for s in split_sentences(text) if len(s) >= min_len]
            for idx, sent in enumerate(sentences):
                if self.app_state.dedup_df is not None:
                    title_series = self.app_state.dedup_df.loc[self.app_state.dedup_df["key"] == row.get("key"), "Title"]
                    title_val = title_series.iloc[0] if not title_series.empty else ""
                else:
                    title_val = ""
                sentence_rows.append(
                    {
                        "sent_id": f"{row.get('key')}-{idx}",
                        "key": row.get("key"),
                        "Date": row.get("Date"),
                        "month": row.get("month"),
                        "Page Type": row.get("Page Type"),
                        "Title": title_val,
                        "sentence_clean": sent,
                    }
                )
        sentence_df = pd.DataFrame(sentence_rows)
        gemini_results = []
        evidence_df = pd.DataFrame()
        if api_key and not sentence_df.empty:
            gemini_results = gemini_client.run_gemini(api_key, [(row["sent_id"], row["sentence_clean"]) for _, row in sentence_df.iterrows()])
            evidence_df = pd.DataFrame(
                [
                    {
                        "key": g.get("sent_id"),
                        **ev,
                    }
                    for g in gemini_results
                    for ev in g.get("evidences", [])
                ]
            )
        self.app_state.gemini_evidence_df = evidence_df
        sentiment_rules = {
            "profanity_mode": self.profanity_mode.currentText(),
            "profanity_scope": self.profanity_scope.currentText(),
            "profanity_per_hit_delta": int(self.profanity_delta.currentText()),
            "profanity_fixed_list": [w.strip() for w in self.profanity_list.toPlainText().splitlines() if w.strip()],
            "context_mode": self.context_mode.currentText(),
        }
        if self.app_state.toxicity_detail_df is None and self.app_state.tokens_df is not None:
            tox_detail, tox_summary = toxicity.scan_dataframe(
                self.app_state.tokens_df,
                text_col="clean_text",
                dictionaries=toxicity.DEFAULT_DICTS,
                whitelist=[],
                context_mode=self.context_mode.currentText(),
            )
            self.app_state.toxicity_detail_df = tox_detail
            self.app_state.toxicity_summary_df = tox_summary
        base_df = pd.DataFrame(
            {
                "key": sentence_df["key"],
                "clean_text": sentence_df["sentence_clean"],
                "raw_text": sentence_df["sentence_clean"],
                "summary_ko": [g.get("summary_ko", "") for g in gemini_results] if gemini_results else [""] * len(sentence_df),
            }
        )
        sentiment_sentence_df = rules_engine.build_sentiment_df(base_df, evidence_df, sentiment_rules, toxicity_df=self.app_state.toxicity_detail_df)
        self.app_state.sentiment_sentence_df = sentiment_sentence_df
        doc_df = (
            sentiment_sentence_df.groupby("key")
            .agg(doc_score_5=("score_5", "mean"), toxicity_level=("toxicity_level", lambda x: x.mode().iat[0] if not x.empty else None))
            .reset_index()
        )
        self.app_state.sentiment_doc_df = doc_df
        month_df = (
            sentence_df.join(sentiment_sentence_df.set_index("key"), on="key", lsuffix="_base")
            .groupby("month")
            .agg(mean_score=("score_5", "mean"), toxicity_high_rate=("toxicity_level", lambda x: (x == "HIGH").mean() if len(x) else 0))
            .reset_index()
        )
        self.app_state.sentiment_month_df = month_df
        self.app_state.sentiment_df = sentiment_sentence_df
        self.sentiment_model.update(sentiment_sentence_df)
        self.status_strip.update(len(sentiment_sentence_df), self.app_state.period_unit, self.app_state.runtime_options.get("news_excluded", False))
        self.app_state.update_log("sentiment", "completed", {"rows": len(sentiment_sentence_df)})
