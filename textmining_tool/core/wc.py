from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional
import sys
import os

from wordcloud import WordCloud


def resource_path(relative: str) -> Path:
    """Return absolute path for resources (handles PyInstaller _MEIPASS)."""
    base_path = getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2])
    return Path(base_path) / relative


def generate_wordcloud(tokens: Iterable[str], font_path: Optional[str], output_path: str | Path) -> Path:
    text = " ".join(tokens)
    kwargs = {"width": 800, "height": 600, "background_color": "white"}
    if font_path and os.path.exists(font_path):
        kwargs["font_path"] = str(font_path)
    wc = WordCloud(**kwargs)
    wc.generate(text)
    output_path = Path(output_path)
    wc.to_file(output_path)
    return output_path
