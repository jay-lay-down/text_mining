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
    tokens_list = [str(t) for t in tokens if str(t).strip()]
    if not tokens_list:
        raise ValueError("워드클라우드를 생성할 토큰이 없습니다.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    kwargs = {"width": 800, "height": 600, "background_color": "white"}

    # Prefer provided font_path, otherwise fall back to bundled NanumGothic (PyInstaller-safe).
    candidate_paths = []
    if font_path:
        candidate_paths.append(Path(font_path))
    candidate_paths.append(resource_path("assets/fonts/NanumGothic.ttf"))
    for cand in candidate_paths:
        if cand and cand.exists():
            kwargs["font_path"] = str(cand)
            break

    try:
        wc = WordCloud(**kwargs)
        wc.generate(" ".join(tokens_list))
        wc.to_file(output_path)
        return output_path
    except Exception as exc:  # noqa: BLE001
        # Re-raise with more context so UI can display a clear message
        raise RuntimeError(f"워드클라우드 생성 실패: {exc}") from exc
