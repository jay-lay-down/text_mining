from __future__ import annotations

import hashlib
from typing import Dict, Iterable, List, Optional

import pandas as pd
from rapidfuzz import fuzz, process


REQUIRED_COLUMNS = ["Date", "Title", "Full Text", "Page Type"]


def map_columns(df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
    missing = [k for k, v in mapping.items() if v is None]
    if missing:
        raise ValueError(f"Missing mapping for: {', '.join(missing)}")
    renamed = df.rename(columns={mapping[k]: k for k in mapping})
    if "Date" in renamed.columns:
        renamed["Date"] = pd.to_datetime(renamed["Date"], errors="coerce")
    return renamed


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
