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

    # Discover models that support generateContent; fall back to a safe shortlist.
    candidate_models: List[str] = []
    try:
        for m in client.models.list():
            methods = getattr(m, "supported_generation_methods", None) or []
            if "generateContent" in methods and m.name:
                candidate_models.append(m.name)
    except Exception:
        candidate_models = []

    if not candidate_models:
        candidate_models = [
            "models/gemini-1.5-pro",
            "models/gemini-1.5-flash",
            "models/gemini-3.5-pro-preview",
        ]

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
            raise RuntimeError(f"Gemini 호출 실패 (모든 모델 시도): {last_error}") from last_error
    return results
