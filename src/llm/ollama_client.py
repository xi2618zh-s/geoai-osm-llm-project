# src/llm/ollama_client.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional
import json

try:
    from ollama import chat
except Exception:
    chat = None


@dataclass
class LLMResult:
    ok: bool
    data: Dict[str, Any]
    raw: str


def call_ollama_json(model: str, system: str, user: str, timeout_s: int = 60) -> LLMResult:
    """
    Calls Ollama chat model and tries to parse JSON from its response.
    """
    if chat is None:
        return LLMResult(ok=False, data={}, raw="ollama python package not available")

    try:
        resp = chat(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = resp["message"]["content"]
    except Exception as e:
        return LLMResult(ok=False, data={}, raw=str(e))

    # Try parse JSON (strict)
    try:
        data = json.loads(content)
        return LLMResult(ok=True, data=data, raw=content)
    except Exception:
        # Try to extract first JSON object
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(content[start : end + 1])
                return LLMResult(ok=True, data=data, raw=content)
            except Exception:
                pass
        return LLMResult(ok=False, data={}, raw=content)
