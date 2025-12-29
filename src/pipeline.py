# src/pipeline.py
from pathlib import Path
from typing import Dict, Any, Optional
import re

from src.config import OSM_PBF, OUTPUT_DIR, OUTPUT_GEOJSON
from src.rag.retriever import FaissRetriever, pick_tag_from_chunks
from src.osm.extractor import extract_nodes_to_geojson, osmium_extract_bbox
from src.osm.geocode import geocode_to_bbox
from src.query.llm_parser import llm_parse_query

DEFAULT_PLACE = "Lund"

def simple_place_heuristic(query: str) -> Optional[str]:
    # Very simple: look for "in <Place>"
    m = re.search(r"\bin\s+([A-Za-zÅÄÖåäö\- ]{2,})$", query.strip())
    if m:
        return m.group(1).strip()
    return None

def run_query(query: str, model: str = "mistral") -> Dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    retriever = FaissRetriever()
    chunks = retriever.retrieve(query, k=5)

    # 1) LLM parse (place + tag) using evidence
    llm_res = llm_parse_query(query=query, chunks=chunks, model=model)

    # 2) Decide place
    place = None
    if llm_res.get("ok"):
        place = llm_res["data"].get("place")
    if not place:
        place = simple_place_heuristic(query) or DEFAULT_PLACE

    # 3) Decide tag
    if llm_res.get("ok"):
        tag = llm_res["data"].get("tag") or {}
        key = tag.get("key")
        value = tag.get("value")
    else:
        key = value = None

    if not key or not value:
        # fallback to robust voting from RAG chunks
        key, value = pick_tag_from_chunks(chunks)

    # 4) bbox + extract subset
    bbox = geocode_to_bbox(place)
    sub_pbf = OUTPUT_DIR / f"sub_{place.lower().replace(' ', '_')}.osm.pbf"
    osmium_extract_bbox(Path(OSM_PBF), sub_pbf, bbox)

    # 5) parse subset + export
    rows = extract_nodes_to_geojson(sub_pbf, key, value, Path(OUTPUT_GEOJSON))

    evidence = [
        {
            "score": c.score,
            "key": c.key,
            "value": c.value,
            "url": c.url,
            "snippet": c.page_content[:220].replace("\n", " "),
        }
        for c in chunks
    ]

    return {
        "query": query,
        "place": place,
        "chosen_tag": f"{key}={value}",
        "bbox": bbox,
        "count": len(rows),
        "geojson_path": str(OUTPUT_GEOJSON),
        "evidence": evidence,
        "llm_ok": bool(llm_res.get("ok")),
        "llm_raw": llm_res.get("raw", ""),
    }
