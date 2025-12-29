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
    candidate_models = [
        "gemini-1.5-pro",
        "gemini-1.5-pro-001",
        "gemini-1.5-flash",
        "gemini-1.5-flash-001",
        "gemini-3.5-pro-preview",
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
            except genai_errors.NotFound as nf_err:
                last_error = nf_err
                continue
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                break
        else:
            raise RuntimeError(f"Gemini 호출 실패 (모든 모델 시도): {last_error}") from last_error
    return results
