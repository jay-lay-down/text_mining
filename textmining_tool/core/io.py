from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


def load_table(path: str | Path, encoding: Optional[str] = None) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    return pd.read_csv(path, encoding=encoding or "utf-8", engine="python")


def save_excel(path: str | Path, df: pd.DataFrame) -> None:
    path = Path(path)
    df.to_excel(path, index=False)
