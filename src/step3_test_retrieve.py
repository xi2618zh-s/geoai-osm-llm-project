# src/step3_test_retrieve.py
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from src.config import FAISS_INDEX, FAISS_META

def main():
    index = faiss.read_index(str(FAISS_INDEX))
    meta = json.load(open(FAISS_META, "r", encoding="utf-8"))

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    query = "What does amenity=cafe mean? How to map it?"
    q = model.encode(query, normalize_embeddings=True).astype(np.float32)[None, :]

    D, I = index.search(q, 5)
    print("Top-5 results:\n")
    for rank, idx in enumerate(I[0], 1):
        m = meta[idx]
        print(f"#{rank} score={D[0][rank-1]:.3f} key={m.get('key')} value={m.get('value')}")
        print(m.get("title"))
        print(m.get("url"))
        print(m.get("page_content")[:400].replace("\n", " ") + " ...")
        print("-" * 80)

if __name__ == "__main__":
    main()
