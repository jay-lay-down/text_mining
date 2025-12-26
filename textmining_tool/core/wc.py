from __future__ import annotations

from pathlib import Path
from typing import Iterable

from wordcloud import WordCloud


def generate_wordcloud(tokens: Iterable[str], font_path: str, output_path: str | Path) -> Path:
    text = " ".join(tokens)
    wc = WordCloud(font_path=str(font_path), width=800, height=600, background_color="white")
    wc.generate(text)
    output_path = Path(output_path)
    wc.to_file(output_path)
    return output_path
