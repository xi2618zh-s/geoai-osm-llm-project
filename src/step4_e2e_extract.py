# src/step4_e2e_extract.py
from pathlib import Path

from src.config import OSM_PBF, OUTPUT_GEOJSON, OUTPUT_DIR
from src.rag.retriever import FaissRetriever, pick_tag_from_chunks
from src.osm.extractor import extract_nodes_to_geojson, osmium_extract_bbox
from src.osm.geocode import geocode_to_bbox

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    query = "Find all bus stops in Lund"

    retriever = FaissRetriever()
    chunks = retriever.retrieve(query, k=5)
    key, value = pick_tag_from_chunks(chunks)

    print(f"User query: {query}")
    print(f"Chosen tag: {key}={value}\n")

    # 1) geocode place -> bbox
    place = "Lund"
    bbox = geocode_to_bbox(place)
    print(f"[DEBUG] bbox for {place}: {bbox}")

    # 2) bbox extract
    sub_pbf = OUTPUT_DIR / f"sub_{place.lower()}.osm.pbf"
    print("[DEBUG] extracting bbox subset ...")
    osmium_extract_bbox(
        input_pbf=Path(OSM_PBF),
        output_pbf=sub_pbf,
        bbox=bbox,
    )
    print("[DEBUG] bbox extraction done.")

    # 3) scan small pbf
    print("[DEBUG] start extracting nodes ...")
    rows = extract_nodes_to_geojson(
        input_pbf=sub_pbf,
        key=key,
        value=value,
        out_geojson=Path(OUTPUT_GEOJSON),
    )
    print("[DEBUG] finished extracting nodes.")

    print(f"\nExtracted nodes: {len(rows)}")
    print(f"GeoJSON saved: {OUTPUT_GEOJSON}")

if __name__ == "__main__":
    main()
