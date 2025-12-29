from __future__ import annotations

import hashlib
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd
from rapidfuzz import fuzz, process


REQUIRED_COLUMNS = ["Date", "Title", "Full Text", "Page Type"]

NAME_HINTS = {
    "dt": ["date", "datetime", "time", "posted", "등록", "작성"],
    "text": ["text", "본문", "content", "body", "review"],
    "title": ["title", "subject", "headline"],
    "source_type": ["type", "channel", "platform", "media", "page", "source"],
    "url": ["url", "link", "href"],
    "author": ["author", "writer", "nick", "user"],
}


def map_columns(df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
    missing = [k for k, v in mapping.items() if v is None]
    if missing:
        raise ValueError(f"Missing mapping for: {', '.join(missing)}")
    renamed = df.rename(columns={mapping[k]: k for k in mapping})
    if "Date" in renamed.columns:
        renamed["Date"] = pd.to_datetime(renamed["Date"], errors="coerce")
    return renamed


def profile_columns(df: pd.DataFrame) -> Dict[str, List[str]]:
    suggestions: Dict[str, List[str]] = {k: [] for k in NAME_HINTS}
    lowered = {c: c.lower() for c in df.columns}
    for role, hints in NAME_HINTS.items():
        for col, low in lowered.items():
            if any(h in low for h in hints):
                suggestions[role].append(col)
    # add heuristics for datetime
    for col in df.columns:
        sample = df[col].dropna().astype(str).head(50)
        parse_success = pd.to_datetime(sample, errors="coerce").notna().mean() if not sample.empty else 0
        if parse_success > 0.6 and col not in suggestions["dt"]:
            suggestions["dt"].append(col)
        avg_len = sample.str.len().mean() if not sample.empty else 0
        unique_ratio = sample.nunique() / len(sample) if len(sample) else 0
        if avg_len > 30 and unique_ratio > 0.5 and col not in suggestions["text"]:
            suggestions["text"].append(col)
        if 5 < avg_len < 40 and unique_ratio > 0.2 and col not in suggestions["title"]:
            suggestions["title"].append(col)
    return suggestions


def build_canonical(
    df: pd.DataFrame,
    dt_col: str,
    text_cols: Sequence[str],
    title_col: Optional[str],
    source_type_col: Optional[str],
    extra_dims: Sequence[str],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    work = df.copy()
    work["dt"] = pd.to_datetime(work[dt_col], errors="coerce")
    work["text"] = work[text_cols].astype(str).agg(" ".join, axis=1).str.strip()
    work["title"] = work[title_col] if title_col else ""
    work["source_type"] = work[source_type_col] if source_type_col else ""
    for dim in extra_dims:
        work[f"dim_{dim}"] = work[dim]
    key_parts = work[["dt", "title", "text", "source_type"] + [f"dim_{d}" for d in extra_dims] if extra_dims else []].astype(str).agg("|".join, axis=1)
    work["doc_id"] = key_parts.apply(lambda x: hashlib.sha1(x.encode("utf-8")).hexdigest())
    canonical_cols = ["doc_id", "dt", "text", "title", "source_type"] + [f"dim_{d}" for d in extra_dims]
    canonical_df = work[canonical_cols]
    mapping_df = pd.DataFrame(
        {
            "dt_col": [dt_col],
            "text_cols": [list(text_cols)],
            "title_col": [title_col],
            "source_type_col": [source_type_col],
            "extra_dims": [list(extra_dims)],
        }
    )
    return canonical_df, mapping_df


def filter_page_types(df: pd.DataFrame, allowed: Iterable[str], exclude_news: bool) -> pd.DataFrame:
    if "Page Type" not in df.columns:
        return df
    result = df.copy()
    if allowed:
        result = result[result["Page Type"].isin(list(allowed))]
    if exclude_news:
        result = result[result["Page Type"].str.lower() != "news"]
    return result


def build_key(row: pd.Series) -> str:
    parts = [str(row.get(col, "")) for col in ["Date", "Title", "Full Text", "Page Type"]]
    key_source = "|".join(parts).strip().lower()
    key_source = " ".join(key_source.split())
    return hashlib.sha1(key_source.encode("utf-8")).hexdigest()


def generate_keys(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["key"] = df.apply(build_key, axis=1)
    return df


def remove_exact_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if "key" not in df.columns:
        raise ValueError("key column is required for duplicate removal")
    deduped = df.drop_duplicates(subset=["key"], keep="first")
    removed = df[~df.index.isin(deduped.index)]
    return deduped, removed


def remove_similar(df: pd.DataFrame, threshold: int = 95) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Naive similarity-based dedup using rapidfuzz on title+text."""
    if df.empty:
        return df, df
    merged = df.copy()
    merged["_concat"] = (merged.get("Title", "") + " " + merged.get("Full Text", "")).fillna("")
    selected_indices: List[int] = []
    removed_rows: List[int] = []
    for idx, text in merged["_concat"].items():
        if idx in removed_rows:
            continue
        selected_indices.append(idx)
        matches = process.extract(text, merged["_concat"].to_dict(), scorer=fuzz.token_set_ratio, limit=None)
        for match_idx, score, _ in matches:
            if match_idx == idx:
                continue
            if score >= threshold:
                removed_rows.append(match_idx)
    deduped = merged.loc[selected_indices].drop(columns=["_concat"]) if selected_indices else merged.drop(columns=["_concat"])  # type: ignore[arg-type]
    removed = merged.loc[removed_rows].drop(columns=["_concat"]) if removed_rows else merged.iloc[0:0]
    return deduped, removed
