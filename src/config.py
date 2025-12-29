from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT / "data"
OSM_PBF = DATA_DIR / "osm" / "sweden-251214.osm.pbf"

WIKI_RAW_DIR = DATA_DIR / "wiki_raw"
WIKI_CHUNKS_DIR = DATA_DIR / "wiki_chunks"

FAISS_DIR = ROOT / "faiss_index"
FAISS_INDEX = FAISS_DIR / "faiss_index"
FAISS_META = FAISS_DIR / "faiss_index.metadata.json"

OUTPUT_DIR = ROOT / "output"
OUTPUT_GEOJSON = OUTPUT_DIR / "output.geojson"
