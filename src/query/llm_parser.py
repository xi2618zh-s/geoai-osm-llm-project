# src/query/llm_parser.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional
from src.llm.ollama_client import call_ollama_json
from src.rag.retriever import RetrievedChunk

SYSTEM_PROMPT = """You are a careful GIS assistant for OpenStreetMap.
You MUST base decisions on the provided evidence (OSM Wiki snippets).
Return ONLY valid JSON. No extra text.

Schema:
{
  "place": "<string or null>",
  "tag": {"key": "<string>", "value": "<string>"},
  "confidence": 0.0-1.0,
  "explanation": "<short>"
}
Rules:
- If place is not explicitly mentioned, set place to null.
- tag.key and tag.value must be a single OSM tag pair like amenity=cafe.
"""

def format_evidence(chunks: List[RetrievedChunk]) -> str:
    lines = []
    for i, c in enumerate(chunks, 1):
        lines.append(f"[{i}] score={c.score:.3f} key={c.key} value={c.value} url={c.url}\n{c.page_content[:500]}")
    return "\n\n".join(lines)

def llm_parse_query(
    query: str,
    chunks: List[RetrievedChunk],
    model: str = "mistral",
) -> Dict[str, Any]:
    evidence = format_evidence(chunks)
    user_prompt = f"""User query:
{query}

Evidence (OSM Wiki snippets):
{evidence}

Return JSON with extracted place and best tag choice."""
    res = call_ollama_json(model=model, system=SYSTEM_PROMPT, user=user_prompt)
    if res.ok:
        return {"ok": True, "data": res.data, "raw": res.raw}
    return {"ok": False, "data": {}, "raw": res.raw}
