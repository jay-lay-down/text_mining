from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

import pandas as pd


DEFAULT_DICTS = {
    "PROFANITY_TOKENS": ["씨발", "ㅅㅂ", "좆", "병신", "개새끼"],
    "POS_CUES": ["좋", "대박", "최고", "추천", "만족", "개꿀", "사랑", "감동"],
    "NEG_CUES": ["싫", "최악", "별로", "불만", "실망", "화남", "빡침", "짜증", "환불", "불매"],
    "TARGET_CUES": ["너", "니", "님", "걔", "저놈", "저년", "작성자", "판매자", "업체", "직원"],
    "INSULT_SUFFIX": ["새끼", "병신", "좆같", "꺼져", "닥쳐", "뒤져"],
    "EMO_POS": ["ㅠㅠ", "ㅜㅜ", "😍", "❤️", "ㅋㅋ", "ㅎㅎ"],
    "SLUR_HATE": [],
}


ROLE_SCORES = {
    "EMPHASIS_POS": 0.10,
    "EMPHASIS_NEG": 0.45,
    "GENERAL_EXPLETIVE": 0.35,
    "TARGETED_INSULT": 0.85,
    "SLUR_HATE": 0.95,
}

TOXICITY_LEVELS = [
    (0.8, "HIGH"),
    (0.4, "MED"),
    (0.0, "LOW"),
]


@dataclass
class RoleResult:
    token: str
    role: str
    window: str


def _window_tokens(tokens: List[str], idx: int, size: int = 3) -> str:
    start = max(idx - size, 0)
    end = min(idx + size + 1, len(tokens))
    return " ".join(tokens[start:end])


def detect_roles(text: str, dictionaries: Dict[str, List[str]], whitelist_patterns: Iterable[str] | None = None) -> Tuple[List[str], List[RoleResult], bool]:
    whitelist_patterns = whitelist_patterns or []
    tokens = text.split()
    profanity_matches: List[str] = []
    roles: List[RoleResult] = []
    targeted = False
    for idx, tok in enumerate(tokens):
        if tok in dictionaries.get("PROFANITY_TOKENS", []):
            window = _window_tokens(tokens, idx)
            for patt in whitelist_patterns:
                if patt in window:
                    roles.append(RoleResult(tok, "EMPHASIS_POS", window))
                    profanity_matches.append(tok)
                    break
            else:
                if any(cue in window for cue in dictionaries.get("SLUR_HATE", [])):
                    role = "SLUR_HATE"
                elif any(cue in window for cue in dictionaries.get("TARGET_CUES", [])) or any(suf in window for suf in dictionaries.get("INSULT_SUFFIX", [])):
                    role = "TARGETED_INSULT"
                    targeted = True
                elif any(cue in window for cue in dictionaries.get("POS_CUES", [])) and not any(cue in window for cue in dictionaries.get("NEG_CUES", [])):
                    role = "EMPHASIS_POS"
                elif any(cue in window for cue in dictionaries.get("NEG_CUES", [])):
                    role = "EMPHASIS_NEG"
                else:
                    role = "GENERAL_EXPLETIVE"
                roles.append(RoleResult(tok, role, window))
                profanity_matches.append(tok)
    return profanity_matches, roles, targeted


def score_toxicity(roles: List[RoleResult]) -> float:
    if not roles:
        return 0.0
    base = max(ROLE_SCORES.get(r.role, 0.0) for r in roles)
    bonus = 0.05 * min(len(roles), 3)
    return min(1.0, max(0.0, base + bonus))


def classify_level(score: float) -> str:
    for threshold, label in TOXICITY_LEVELS:
        if score >= threshold:
            return label
    return "LOW"


def scan_dataframe(df: pd.DataFrame, text_col: str, dictionaries: Dict[str, List[str]], whitelist: Iterable[str] | None = None, context_mode: str = "CONTEXT_AWARE", role_to_delta: Dict[str, int] | None = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    role_to_delta = role_to_delta or {
        "EMPHASIS_POS": 0,
        "GENERAL_EXPLETIVE": -1,
        "EMPHASIS_NEG": -1,
        "TARGETED_INSULT": -2,
        "SLUR_HATE": -2,
    }
    rows = []
    for _, row in df.iterrows():
        text = str(row.get(text_col, ""))
        matches, roles, targeted = detect_roles(text, dictionaries, whitelist)
        score = score_toxicity(roles)
        level = classify_level(score)
        delta = 0
        if context_mode == "ALWAYS_PENALIZE" and matches:
            delta = -2
        elif matches:
            delta = sum(role_to_delta.get(r.role, 0) for r in roles)
            delta = max(-2, min(2, delta))
        roles_json = [r.__dict__ for r in roles]
        rows.append(
            {
                "key": row.get("key"),
                "date": row.get("Date"),
                "month": row.get("month") or row.get("period"),
                "page_type": row.get("Page Type"),
                "title": row.get("Title"),
                "clean_text_snippet": text[:200],
                "raw_text_snippet": str(row.get("Full Text", ""))[:200],
                "toxicity_score": score,
                "toxicity_level": level,
                "targeted_attack": targeted,
                "profanity_count": len(matches),
                "profanity_matches": matches,
                "profanity_roles_json": roles_json,
                "evidence_phrases": [r.window for r in roles],
                "notes": "",
                "profanity_sentiment_delta": delta,
                "context_mode": context_mode,
            }
        )
    detail_df = pd.DataFrame(rows)
    summary_df = (
        detail_df.groupby(["month", "page_type"])
        .agg(
            avg_toxicity=("toxicity_score", "mean"),
            high_count=("toxicity_level", lambda x: (x == "HIGH").sum()),
            count=("key", "count"),
        )
        .reset_index()
    )
    return detail_df, summary_df
