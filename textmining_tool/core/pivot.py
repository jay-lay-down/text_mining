from __future__ import annotations

import pandas as pd


_PERIOD_FORMATS = {
    "year": "%Y",
    "half": None,
    "quarter": None,
    "month": "%Y-%m",
    "week": "%G-W%V",
    "day": "%Y-%m-%d",
    "hour": "%Y-%m-%d %H:00",
}


def add_period_column(df: pd.DataFrame, unit: str) -> pd.DataFrame:
    if "Date" not in df.columns:
        raise ValueError("Date column missing for period derivation")
    if df["Date"].isna().all():
        raise ValueError("Date column is empty after parsing")
    unit = unit.lower()
    result = df.copy()
    date_series = pd.to_datetime(result["Date"], errors="coerce")
    if unit == "half":
        result["period"] = date_series.dt.year.astype(str) + "-H" + (((date_series.dt.month - 1) // 6) + 1).astype(str)
    elif unit == "quarter":
        result["period"] = date_series.dt.year.astype(str) + "-Q" + (((date_series.dt.month - 1) // 3) + 1).astype(str)
    elif unit in _PERIOD_FORMATS and _PERIOD_FORMATS[unit]:
        result["period"] = date_series.dt.strftime(_PERIOD_FORMATS[unit])
    else:
        raise ValueError(f"Unsupported period unit: {unit}")
    return result


def build_pivot(df: pd.DataFrame, unit: str, include_page_type: bool) -> pd.DataFrame:
    enriched = add_period_column(df, unit)
    if include_page_type and "Page Type" in enriched.columns:
        pivoted = enriched.pivot_table(index="period", columns="Page Type", values="key", aggfunc="count", fill_value=0)
    else:
        pivoted = enriched.groupby("period").size().reset_index(name="count")
    return pivoted
