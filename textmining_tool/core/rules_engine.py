from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd


@dataclass
class Evidence:
    phrase: str
    type: str
    strength: str
    aspect: str | None = None
    target: str | None = None


PROFANITY_MODES = {"ONCE_FIXED", "COUNT_ACCUM", "COUNT_CAP_TO_2"}
PROFANITY_SCOPES = {"CLEAN_TEXT_ONLY", "RAW_TEXT_ONLY", "BOTH"}


class RuleEngine:
    def __init__(self, profanity_list: List[str] | None = None) -> None:
        self.profanity_list = profanity_list or []

    def _score_evidence(self, evidence: Evidence) -> int:
        if evidence.type == "positive":
            return 2 if evidence.strength == "strong" else 1
        if evidence.type == "negative":
            return -2 if evidence.strength == "strong" else -1
        return 0

    def _apply_profanity(self, text: str, mode: str, per_hit: int) -> tuple[int, List[str]]:
        matches = [p for p in self.profanity_list if p and p in text]
        count = len(matches)
        if count == 0:
            return 0, []
        if mode == "ONCE_FIXED":
            return -2, matches
        if mode == "COUNT_ACCUM":
            return per_hit * count, matches
        if mode == "COUNT_CAP_TO_2":
            return max(-2, per_hit * count), matches
        return 0, matches

    def score(
        self,
        evidence_rows: List[Dict[str, str]],
        clean_text: str,
        raw_text: str,
        profanity_mode: str,
        profanity_per_hit_delta: int,
        profanity_scope: str,
        profanity_roles: List[Dict[str, str]] | None = None,
        context_mode: str = "CONTEXT_AWARE",
        role_to_delta: Dict[str, int] | None = None,
    ) -> Dict[str, object]:
        evidence_objs = [Evidence(**row) for row in evidence_rows]
        base_scores = [self._score_evidence(e) for e in evidence_objs]
        evidence_adjusted = base_scores.copy()
        # simple intensifier/negation handling could be added here
        scope_text = clean_text if profanity_scope == "CLEAN_TEXT_ONLY" else raw_text
        if profanity_scope == "BOTH":
            scope_text = f"{raw_text} {clean_text}"
        profanity_delta, profanity_matches = self._apply_profanity(scope_text, profanity_mode, profanity_per_hit_delta)
        if context_mode == "CONTEXT_AWARE" and profanity_roles:
            role_to_delta = role_to_delta or {
                "EMPHASIS_POS": 0,
                "GENERAL_EXPLETIVE": -1,
                "EMPHASIS_NEG": -1,
                "TARGETED_INSULT": -2,
                "SLUR_HATE": -2,
            }
            profanity_delta = max(-2, min(2, sum(role_to_delta.get(r.get("role"), 0) for r in profanity_roles)))
        total = max(-2, min(2, sum(evidence_adjusted) + profanity_delta))
        breakdown = {
            "profanity_mode": profanity_mode,
            "profanity_matches": profanity_matches,
            "profanity_delta": profanity_delta,
            "evidences": [e.__dict__ for e in evidence_objs],
            "evidence_scores": evidence_adjusted,
            "total": total,
            "profanity_roles": profanity_roles or [],
            "context_mode": context_mode,
        }
        return {
            "score_5": total,
            "profanity_count": len(profanity_matches),
            "breakdown": breakdown,
        }


def build_sentiment_df(
    df: pd.DataFrame,
    evidence_df: pd.DataFrame,
    rules: Dict[str, object],
    toxicity_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    engine = RuleEngine(rules.get("profanity_fixed_list", []))
    if evidence_df is None or evidence_df.empty:
        evidence_df = pd.DataFrame(columns=["key", "phrase", "type", "strength", "aspect", "target"])
    if "key" not in evidence_df.columns:
        evidence_df["key"] = []
    results = []
    for _, row in df.iterrows():
        evidences = evidence_df[evidence_df["key"] == row.get("key")]
        evidence_rows = evidences.to_dict(orient="records") if not evidences.empty else []
        tox_roles: List[Dict[str, str]] = []
        tox_level = None
        tox_delta = 0
        targeted = False
        profanity_matches = []
        tox_row = pd.DataFrame()
        if toxicity_df is not None and not toxicity_df.empty:
            tox_row = toxicity_df[toxicity_df["key"] == row.get("key")]
            if not tox_row.empty:
                tox_roles = tox_row.iloc[0].get("profanity_roles_json", []) or []
                tox_level = tox_row.iloc[0].get("toxicity_level")
                tox_delta = tox_row.iloc[0].get("profanity_sentiment_delta", 0)
                targeted = bool(tox_row.iloc[0].get("targeted_attack", False))
                profanity_matches = tox_row.iloc[0].get("profanity_matches", [])
        scored = engine.score(
            evidence_rows,
            clean_text=row.get("clean_text", ""),
            raw_text=row.get("raw_text", ""),
            profanity_mode=rules.get("profanity_mode", "ONCE_FIXED"),
            profanity_per_hit_delta=rules.get("profanity_per_hit_delta", -2),
            profanity_scope=rules.get("profanity_scope", "CLEAN_TEXT_ONLY"),
            profanity_roles=tox_roles,
            context_mode=rules.get("context_mode", "CONTEXT_AWARE"),
            role_to_delta=rules.get("role_to_delta"),
        )
        results.append(
            {
                "key": row.get("key"),
                "score_5": scored["score_5"],
                "summary_ko": row.get("summary_ko", ""),
                "evidences_json": evidence_rows,
                "rule_breakdown_json": scored["breakdown"],
                "profanity_count": scored["profanity_count"],
                "profanity_matches": profanity_matches or scored["breakdown"].get("profanity_matches", []),
                "profanity_mode": rules.get("profanity_mode"),
                "toxicity_level": tox_level,
                "targeted_attack": targeted,
                "profanity_roles_json": tox_roles,
                "toxicity_score": tox_row.iloc[0].get("toxicity_score") if toxicity_df is not None and not toxicity_df.empty and not tox_row.empty else None,
                "profanity_sentiment_delta": tox_delta,
                "context_mode": rules.get("context_mode", "CONTEXT_AWARE"),
            }
        )
    return pd.DataFrame(results)
