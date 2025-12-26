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


def add_period_column(df: pd.DataFrame, unit: str, dt_col: str = "Date") -> pd.DataFrame:
    if dt_col not in df.columns:
        raise ValueError("Date column missing for period derivation")
    if df[dt_col].isna().all():
        raise ValueError("Date column is empty after parsing")
    unit = unit.lower()
    result = df.copy()
    date_series = pd.to_datetime(result[dt_col], errors="coerce")
    if unit == "half":
        result["period"] = date_series.dt.year.astype(str) + "-H" + (((date_series.dt.month - 1) // 6) + 1).astype(str)
    elif unit == "quarter":
        result["period"] = date_series.dt.year.astype(str) + "-Q" + (((date_series.dt.month - 1) // 3) + 1).astype(str)
    elif unit in _PERIOD_FORMATS and _PERIOD_FORMATS[unit]:
        result["period"] = date_series.dt.strftime(_PERIOD_FORMATS[unit])
    else:
        raise ValueError(f"Unsupported period unit: {unit}")
    return result


def build_pivot(df: pd.DataFrame, unit: str, include_page_type: bool, group_dims: list[str] | None = None, dt_col: str = "Date") -> pd.DataFrame:
    enriched = add_period_column(df, unit, dt_col=dt_col)
    group_dims = group_dims or []
    group_cols = ["period"] + group_dims
    if include_page_type and "Page Type" in enriched.columns and "Page Type" not in group_cols:
        group_cols.append("Page Type")
    pivoted = enriched.groupby(group_cols).size().reset_index(name="count")
    return pivoted
