from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class AppState:
    """Central state container shared across pages."""

    raw_df: Optional[pd.DataFrame] = None
    filtered_df: Optional[pd.DataFrame] = None
    dedup_df: Optional[pd.DataFrame] = None
    canonical_df: Optional[pd.DataFrame] = None

    date_col: Optional[str] = None
    title_col: Optional[str] = None
    text_col: Optional[str] = None
    page_type_col: Optional[str] = None
    url_col: Optional[str] = None

    period_unit: str = "month"
    time_grain: str = "month"
    selected_dims: list[str] = field(default_factory=list)
    schema_mapping: Dict[str, Any] = field(default_factory=dict)

    pivot_df: Optional[pd.DataFrame] = None
    verbatim_df: Optional[pd.DataFrame] = None

    tokens_df: Optional[pd.DataFrame] = None
    freq_df: Optional[pd.DataFrame] = None
    top50_df: Optional[pd.DataFrame] = None
    monthly_top_df: Optional[pd.DataFrame] = None

    sentiment_df: Optional[pd.DataFrame] = None
    sentiment_sentence_df: Optional[pd.DataFrame] = None
    sentiment_doc_df: Optional[pd.DataFrame] = None
    sentiment_month_df: Optional[pd.DataFrame] = None
    gemini_evidence_df: Optional[pd.DataFrame] = None

    rules_df: Optional[pd.DataFrame] = None
    nodes_df: Optional[pd.DataFrame] = None
    edges_df: Optional[pd.DataFrame] = None
    pyvis_html_path: Optional[Path] = None

    toxicity_detail_df: Optional[pd.DataFrame] = None
    toxicity_summary_df: Optional[pd.DataFrame] = None
    audit_report_df: Optional[pd.DataFrame] = None
    audit_snippets_df: Optional[pd.DataFrame] = None
    empty_doc_report_df: Optional[pd.DataFrame] = None
    schema_mapping_df: Optional[pd.DataFrame] = None
    canonical_export_df: Optional[pd.DataFrame] = None

    export_sheet_flags: Dict[str, bool] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)

    runtime_options: Dict[str, Any] = field(
        default_factory=lambda: {
            "news_excluded": False,
            "page_type_filter": [],
            "remove_similar": False,
            "similarity_threshold": 95,
            "cleaning": {
                "korean_only": True,
                "keep_number": False,
                "keep_english": False,
                "remove_url": True,
                "remove_email": True,
                "remove_hashtag": True,
                "remove_mention": True,
                "strip_whitespace": True,
                "min_length": 2,
                "pos": "noun",
                "min_freq": 2,
            },
            "profanity": {
                "mode": "ONCE_FIXED",
                "per_hit_delta": -2,
                "scope": "CLEAN_TEXT_ONLY",
            },
        }
    )

    def update_log(self, stage: str, message: str, payload: Optional[Dict[str, Any]] = None) -> None:
        entry = {"stage": stage, "message": message}
        if payload:
            entry.update(payload)
        self.logs.append(entry)


DEFAULT_EXPORT_SHEETS = [
    "raw_original",
    "preprocessed_filtered",
    "preprocessed_dedup",
    "buzz_pivot",
    "verbatim",
    "token_freq",
    "top50_preview",
    "monthly_top_words",
    "sentiment_sentence",
    "sentiment_doc",
    "sentiment_month",
    "apriori_rules",
    "network_nodes",
    "network_edges",
    "toxicity_detail",
    "toxicity_summary",
    "audit_report",
    "audit_snippets",
    "empty_doc_report",
    "logs",
]
