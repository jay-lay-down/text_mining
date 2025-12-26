from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable

import pandas as pd
from pandas import ExcelWriter

from .state import AppState


SHEET_MAPPING = {
    "raw_original": "raw_df",
    "preprocessed_filtered": "filtered_df",
    "preprocessed_dedup": "dedup_df",
    "canonical_docs": "canonical_export_df",
    "schema_mapping": "schema_mapping_df",
    "buzz_pivot": "pivot_df",
    "verbatim": "verbatim_df",
    "token_freq": "freq_df",
    "top50_preview": "top50_df",
    "monthly_top_words": "monthly_top_df",
    "sentiment_sentence": "sentiment_sentence_df",
    "sentiment_doc": "sentiment_doc_df",
    "sentiment_month": "sentiment_month_df",
    "toxicity_detail": "toxicity_detail_df",
    "toxicity_summary": "toxicity_summary_df",
    "audit_report": "audit_report_df",
    "audit_snippets": "audit_snippets_df",
    "empty_doc_report": "empty_doc_report_df",
    "apriori_rules": "rules_df",
    "network_nodes": "nodes_df",
    "network_edges": "edges_df",
    "logs": "logs",
}


def export_selected_sheets(path: str | Path, app_state: AppState, selected_sheets: Iterable[str], include_empty: bool = False) -> None:
    path = Path(path)
    if not selected_sheets:
        raise ValueError("No sheets selected")
    with ExcelWriter(path, engine="xlsxwriter") as writer:
        for sheet in selected_sheets:
            attr = SHEET_MAPPING.get(sheet)
            data = getattr(app_state, attr, None)
            if data is None:
                if include_empty:
                    pd.DataFrame().to_excel(writer, sheet_name=sheet, index=False)
                continue
            if isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = data if isinstance(data, pd.DataFrame) else pd.DataFrame()
            if df.empty and not include_empty:
                continue
            df.to_excel(writer, sheet_name=sheet, index=False)
