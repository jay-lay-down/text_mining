from __future__ import annotations

import traceback
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
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
        self.summary_model = PandasModel(pd.DataFrame())
        self.summary_table = QTableView()
        self.summary_table.setModel(self.summary_model)
        self.voc_model = PandasModel(pd.DataFrame())
        self.voc_table = QTableView()
        self.voc_table.setModel(self.voc_model)
        self.chart_label = QLabel()
        self.chart_label.setMinimumHeight(220)
        self.status_strip = StatusStrip()
        self._build_ui()

    def _build_ui(self) -> None:
        form = QFormLayout()
        form.setVerticalSpacing(6)
        form.addRow("Gemini API Key", self.api_key_edit)
        form.addRow("욕설 모드", self.profanity_mode)
        form.addRow("욕설 스코프", self.profanity_scope)
        form.addRow("욕설 패널티", self.profanity_delta)
        form.addRow("Context 모드", self.context_mode)
        form.addRow("최소 문장 길이", self.min_sentence_len)
        form.addRow("욕설 리스트", self.profanity_list)
        cfg_box = QGroupBox("감성 설정")
        cfg_box.setLayout(form)
        cfg_box.setMaximumHeight(260)

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
        layout.addWidget(QLabel("감성 점수 분포"))
        layout.addWidget(self.chart_label)
        layout.addWidget(QLabel("점수 요약"))
        layout.addWidget(self.summary_table)
        layout.addWidget(QLabel("문장/VOC"))
        layout.addWidget(self.voc_table)
        layout.addWidget(self.sentiment_table)
        layout.addWidget(self.status_strip)
        layout.addStretch()
        self.setLayout(layout)

    def run_sentiment(self) -> None:
        if self.app_state.tokens_df is None or self.app_state.tokens_df.empty:
            QMessageBox.warning(self, "감성 분석", "텍스트마이닝 결과가 없습니다. 먼저 텍스트마이닝을 실행하세요.")
            return
        try:
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
            if sentence_df.empty:
                QMessageBox.warning(self, "감성 분석", "문장 단위 텍스트가 없습니다. 옵션을 완화하거나 데이터를 확인하세요.")
                return
            gemini_results = []
            evidence_df = pd.DataFrame()
            if api_key:
                try:
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
                except Exception as exc:  # noqa: BLE001
                    detail = traceback.format_exc()
                    QMessageBox.warning(self, "Gemini 호출 실패", f"Gemini 호출에 실패했습니다. 룰 기반으로만 진행합니다.\n{exc}\n\n{detail}")
            self.app_state.gemini_evidence_df = evidence_df
            sentiment_rules = {
                "profanity_mode": self.profanity_mode.currentText(),
                "profanity_scope": self.profanity_scope.currentText(),
                "profanity_per_hit_delta": int(self.profanity_delta.currentText()),
                "profanity_fixed_list": [w.strip() for w in self.profanity_list.toPlainText().splitlines() if w.strip()],
                "context_mode": self.context_mode.currentText(),
            }
            if self.app_state.toxicity_detail_df is None and self.app_state.tokens_df is not None:
                try:
                    tox_detail, tox_summary = toxicity.scan_dataframe(
                        self.app_state.tokens_df,
                        text_col="clean_text",
                        dictionaries=toxicity.DEFAULT_DICTS,
                        whitelist=[],
                        context_mode=self.context_mode.currentText(),
                    )
                    self.app_state.toxicity_detail_df = tox_detail
                    self.app_state.toxicity_summary_df = tox_summary
                except Exception as exc:  # noqa: BLE001
                    QMessageBox.warning(self, "유해성 스캔 실패", f"유해성 스캔 중 오류가 발생했습니다. 감성만 계속합니다.\n{exc}")
            # key가 없으면 sent_id로 대체
            base_df = pd.DataFrame(
                {
                    "key": sentence_df.get("key", sentence_df["sent_id"]),
                    "clean_text": sentence_df["sentence_clean"],
                    "raw_text": sentence_df["sentence_clean"],
                    "summary_ko": [g.get("summary_ko", "") for g in gemini_results] if gemini_results else [""] * len(sentence_df),
                }
            )
            sentiment_sentence_df = rules_engine.build_sentiment_df(base_df, evidence_df, sentiment_rules, toxicity_df=self.app_state.toxicity_detail_df)
            self.app_state.sentiment_sentence_df = sentiment_sentence_df
            # 요약 테이블
            score_counts = sentiment_sentence_df["score_5"].value_counts().reindex([-2, -1, 0, 1, 2], fill_value=0)
            summary_df = score_counts.reset_index()
            summary_df.columns = ["score_5", "count"]
            self.summary_model.update(summary_df)
            # VOC: 상위 강한 부정/긍정 20개
            voc_df = sentiment_sentence_df.sort_values("score_5").head(20)[["sentence_clean", "score_5", "toxicity_level"]]
            self.voc_model.update(voc_df)
            # 바차트 생성
            try:
                colors = {-2: "#b30000", -1: "#e55c5c", 0: "#888888", 1: "#4a90e2", 2: "#003f8c"}
                fig, ax = plt.subplots(figsize=(6, 2.4))
                bars = ax.bar([str(k) for k in score_counts.index], score_counts.values, color=[colors[k] for k in score_counts.index])
                ax.set_title("감성 점수 분포")
                ax.set_ylabel("건수")
                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width() / 2, height, f"{int(height)}", ha="center", va="bottom", fontsize=8)
                fig.tight_layout()
                assets_dir = Path(__file__).resolve().parents[2] / "assets"
                assets_dir.mkdir(parents=True, exist_ok=True)
                chart_path = assets_dir / "sentiment_chart.png"
                fig.savefig(chart_path)
                plt.close(fig)
                self.chart_label.setPixmap(QPixmap(str(chart_path)))
            except Exception as exc:  # noqa: BLE001
                detail = traceback.format_exc()
                QMessageBox.warning(self, "차트 생성 실패", f"감성 분포 차트 생성에 실패했습니다.\n{exc}\n\n{detail}")
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
        except Exception as exc:  # noqa: BLE001
            detail = traceback.format_exc()
            QMessageBox.critical(self, "감성 분석 오류", f"감성 분석 중 오류가 발생했습니다: {exc}\n\n{detail}")
