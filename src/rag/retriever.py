# src/rag/retriever.py
from __future__ import annotations
import json
from dataclasses import dataclass
from typing import List, Dict, Tuple

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from src.config import FAISS_INDEX, FAISS_META


@dataclass
class RetrievedChunk:
    score: float
    page_content: str
    url: str
    title: str
    key: str | None
    value: str | None


class FaissRetriever:
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        index_path=FAISS_INDEX,
        meta_path=FAISS_META,
    ):
        self.model = SentenceTransformer(model_name)
        self.index = faiss.read_index(str(index_path))
        with open(meta_path, "r", encoding="utf-8") as f:
            self.meta: List[Dict] = json.load(f)

    def retrieve(self, query: str, k: int = 5) -> List[RetrievedChunk]:
        q = self.model.encode(query, normalize_embeddings=True).astype(np.float32)[None, :]
        D, I = self.index.search(q, k)
        out: List[RetrievedChunk] = []
        for rank, idx in enumerate(I[0]):
            m = self.meta[int(idx)]
            out.append(
                RetrievedChunk(
                    score=float(D[0][rank]),
                    page_content=m.get("page_content", ""),
                    url=m.get("url", ""),
                    title=m.get("title", ""),
                    key=m.get("key"),
                    value=m.get("value"),
                )
            )
        return out


def pick_tag_from_chunks(chunks: List[RetrievedChunk]) -> Tuple[str, str]:
    """
    MVP tag selector: vote by (key,value) weighted by similarity score.
    Returns (key, value).
    """
    votes: Dict[Tuple[str, str], float] = {}
    for c in chunks:
        if c.key and c.value:
            kv = (c.key, c.value)
            votes[kv] = votes.get(kv, 0.0) + c.score

    if not votes:
        raise ValueError("No (key,value) found in retrieved chunks. Expand wiki seeds or adjust parsing.")

    best = max(votes.items(), key=lambda x: x[1])[0]
    return best[0], best[1]
