from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional
import os
import sys

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

    # Prefer provided font_path, otherwise fall back to bundled NanumGothic (PyInstaller-safe).
    candidate_paths = []
    env_font = os.environ.get("TEXTMINING_FONT_PATH")
    if env_font:
        candidate_paths.append(Path(env_font))
    if font_path:
        candidate_paths.append(Path(font_path))
    candidate_paths.append(resource_path("assets", "fonts", "NanumGothic.ttf"))
    candidate_paths.append(resource_path("assets", "fonts", "NanumSquareNeo-bRg.ttf"))
    candidate_paths.append(Path.cwd() / "textmining_tool" / "assets" / "fonts" / "NanumSquareNeo-bRg.ttf")
    candidate_paths.append(Path(r"C:\Users\70089004\tm_test\text_mining\textmining_tool\assets\fonts\NanumSquareNeo-bRg.ttf"))
    chosen_font = None
    for cand in candidate_paths:
        if cand and cand.exists():
            chosen_font = str(cand)
            break

    if not chosen_font:
        raise FileNotFoundError(
            "한글 폰트 파일(NanumGothic.ttf 또는 NanumSquareNeo-bRg.ttf)을 찾을 수 없습니다. "
            "assets/fonts 경로나 번들 포함 여부를 확인하고, 필요 시 TEXTMINING_FONT_PATH 환경변수로 폰트 경로를 지정하세요."
        )

    kwargs["font_path"] = chosen_font

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

    candidate_paths = []
    env_font = os.environ.get("TEXTMINING_FONT_PATH")
    if env_font:
        candidate_paths.append(Path(env_font))
    if font_path:
        candidate_paths.append(Path(font_path))
    candidate_paths.append(resource_path("assets", "fonts", "NanumGothic.ttf"))
    candidate_paths.append(resource_path("assets", "fonts", "NanumSquareNeo-bRg.ttf"))
    candidate_paths.append(Path.cwd() / "textmining_tool" / "assets" / "fonts" / "NanumSquareNeo-bRg.ttf")
    candidate_paths.append(Path(r"C:\Users\70089004\tm_test\text_mining\textmining_tool\assets\fonts\NanumSquareNeo-bRg.ttf"))
    chosen_font = None
    for cand in candidate_paths:
        if cand and cand.exists():
            chosen_font = str(cand)
            break

    if not chosen_font:
        raise FileNotFoundError(
            "한글 폰트 파일(NanumGothic.ttf 또는 NanumSquareNeo-bRg.ttf)을 찾을 수 없습니다. "
            "assets/fonts 경로나 번들 포함 여부를 확인하고, 필요 시 TEXTMINING_FONT_PATH 환경변수로 폰트 경로를 지정하세요."
        )

    kwargs["font_path"] = chosen_font

    try:
        wc = WordCloud(**kwargs)
        wc.generate_from_frequencies(freqs)
        wc.to_file(output_path)
        return output_path
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"워드클라우드 생성 실패: {exc}") from exc
