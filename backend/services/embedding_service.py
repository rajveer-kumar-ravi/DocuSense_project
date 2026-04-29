"""Local HuggingFace sentence-transformer embeddings."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    name = os.environ.get("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    return SentenceTransformer(name)


def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    vecs = _model().encode(texts, show_progress_bar=False, normalize_embeddings=True)
    return [v.tolist() for v in vecs]


def embed_query(text: str) -> List[float]:
    return embed_texts([text])[0]
