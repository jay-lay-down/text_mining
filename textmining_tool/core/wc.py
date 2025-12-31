from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, Optional

from wordcloud import WordCloud


def resource_path(*parts: str) -> Path:
    """Return absolute path for resources (handles PyInstaller _MEIPASS)."""
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base_path.joinpath(*parts) if parts else base_path


def generate_wordcloud(tokens: Iterable[str], font_path: Optional[str], output_path: str | Path) -> Path:
    tokens_list = [str(t) for t in tokens if str(t).strip()]
    if not tokens_list:
        raise ValueError("워드클라우드를 생성할 토큰이 없습니다.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    kwargs = {"width": 800, "height": 600, "background_color": "white"}

    kwargs["font_path"] = _select_font(font_path)

    try:
        wc = WordCloud(**kwargs)
        wc.generate(" ".join(tokens_list))
        wc.to_file(output_path)
        return output_path
    except Exception:
        raise RuntimeError("워드클라우드 생성 실패: 폰트 적용 중 오류가 발생했습니다.")


def generate_wordcloud_from_freq(freqs: dict[str, int], font_path: Optional[str], output_path: str | Path) -> Path:
    """Generate a wordcloud directly from frequency mapping (safer than token repetition)."""
    if not freqs:
        raise ValueError("워드클라우드를 생성할 토큰 빈도가 없습니다.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    kwargs = {"width": 900, "height": 500, "background_color": "white"}

    kwargs["font_path"] = _select_font(font_path)

    try:
        wc = WordCloud(**kwargs)
        wc.generate_from_frequencies(freqs)
        wc.to_file(output_path)
        return output_path
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"워드클라우드 생성 실패: {exc}") from exc


def _select_font(font_path: Optional[str]) -> str:
    """Return the first available font path from user-provided and bundled candidates."""
    candidate_paths = []
    if font_path:
        candidate_paths.append(Path(font_path))

    # Preferred supplied font (user drop-in)
    candidate_paths.append(resource_path("assets", "fonts", "NanumSquareNeo-bRg.ttf"))
    # Legacy bundled font for backward compatibility
    candidate_paths.append(resource_path("assets", "fonts", "NanumGothic.ttf"))
    # Also search non-bundled project-root assets for local runs
    cwd_assets = Path.cwd() / "assets" / "fonts"
    candidate_paths.append(cwd_assets / "NanumSquareNeo-bRg.ttf")
    candidate_paths.append(cwd_assets / "NanumGothic.ttf")

    for cand in candidate_paths:
        if cand and cand.exists():
            return str(cand)

    raise FileNotFoundError(
        "한글 폰트 파일을 찾을 수 없습니다. assets/fonts에 NanumSquareNeo-bRg.ttf (또는 NanumGothic.ttf)을 "
        "복사했는지, PyInstaller 번들에 포함했는지 확인하세요."
    )
