from __future__ import annotations

import json
from typing import Dict, List, Tuple

from google import genai
from google.genai import errors as genai_errors


GEMINI_PROMPT = (
    "You are a Korean sentiment evidence extractor. Respond ONLY with JSON in the shape:\n"
    '{"overall_polarity":"positive|neutral|negative|mixed","overall_intensity":0.0,'
    '"evidences":[{"phrase":"...","type":"positive|negative|profanity|intensifier|negation|sarcasm|other",'
    '"strength":"mild|strong","aspect":"가격|품질|배송|서비스|디자인|기타","target":"..."}],"summary_ko":"..."}'
)


def run_gemini(api_key: str, texts: List[Tuple[str, str]]) -> List[Dict[str, object]]:
    """texts -> list of (key, clean_text)."""
    client = genai.Client(api_key=api_key)

    # Discover models that support generateContent; prioritize Gemini 3.x.
    candidate_models: List[str] = []
    try:
        for m in client.models.list():
            methods = getattr(m, "supported_generation_methods", None) or []
            if "generateContent" in methods and m.name:
                candidate_models.append(m.name)
    except Exception:
        candidate_models = []

    def _prioritize(models: List[str]) -> List[str]:
        # Gemini 3.x first, then 1.5 family.
        pri_3 = [m for m in models if "gemini-3" in m]
        pri_15 = [m for m in models if "gemini-1.5" in m and m not in pri_3]
        others = [m for m in models if m not in pri_3 and m not in pri_15]
        prioritized = pri_3 + pri_15 + others
        # Ensure fully-qualified names
        normalized = []
        for name in prioritized:
            if not name.startswith("models/"):
                normalized.append(f"models/{name}")
            else:
                normalized.append(name)
        # Deduplicate while preserving order
        seen = set()
        ordered = []
        for n in normalized:
            if n not in seen:
                seen.add(n)
                ordered.append(n)
        return ordered

    candidate_models = _prioritize(candidate_models) if candidate_models else []

    if not candidate_models:
        candidate_models = _prioritize(
            [
                "models/gemini-3.0-pro",
                "models/gemini-3.0-flash",
                "models/gemini-1.5-pro",
                "models/gemini-1.5-flash",
                "models/gemini-1.5-flash-001",
            ]
        )

    results: List[Dict[str, object]] = []
    for key, text in texts:
        prompt = GEMINI_PROMPT + f"\nText:\n{text}"
        last_error = None
        for model in candidate_models:
            try:
                resp = client.models.generate_content(model=model, contents=prompt)
                content = resp.text or ""
                parsed = json.loads(content)
                results.append({"key": key, **parsed})
                break
            except genai_errors.ClientError as client_err:
                # Retry on 404/invalid model by moving to the next candidate; otherwise surface.
                msg = str(client_err)
                if "404" in msg or "not found" in msg.lower():
                    last_error = client_err
                    continue
                last_error = client_err
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                break
        else:
            # 모든 후보 실패 시 빈 결과를 반환하고 호출 측에서 룰 기반으로만 진행
            return []
    return results
