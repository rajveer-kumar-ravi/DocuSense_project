"""ChromaDB-backed vector store, embeddings supplied externally."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Dict, List

import chromadb
from chromadb.config import Settings


COLLECTION = "docusense_chunks"


@lru_cache(maxsize=1)
def _client() -> chromadb.api.ClientAPI:
    persist_dir = os.environ.get("CHROMA_DIR", "/app/data/chroma")
    os.makedirs(persist_dir, exist_ok=True)
    return chromadb.PersistentClient(
        path=persist_dir,
        settings=Settings(anonymized_telemetry=False, allow_reset=False),
    )


def _collection():
    # We bring our own embeddings; pass embedding_function=None.
    return _client().get_or_create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
        embedding_function=None,
    )


def add_chunks(
    doc_id: str,
    doc_name: str,
    chunks: List[Dict],
    embeddings: List[List[float]],
) -> int:
    coll = _collection()
    ids = [f"{doc_id}::{c['chunk_index']}" for c in chunks]
    metadatas = [
        {
            "doc_id": doc_id,
            "doc_name": doc_name,
            "page": int(c["page"]),
            "chunk_index": int(c["chunk_index"]),
        }
        for c in chunks
    ]
    documents = [c["text"] for c in chunks]
    coll.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
    return len(ids)


def query(
    embedding: List[float],
    doc_ids: List[str] | None = None,
    top_k: int = 6,
) -> List[Dict]:
    coll = _collection()
    where = None
    if doc_ids:
        if len(doc_ids) == 1:
            where = {"doc_id": doc_ids[0]}
        else:
            where = {"doc_id": {"$in": doc_ids}}
    res = coll.query(query_embeddings=[embedding], n_results=top_k, where=where)
    out: List[Dict] = []
    if not res or not res.get("ids"):
        return out
    ids = res["ids"][0]
    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res.get("distances", [[None] * len(ids)])[0]
    for i, _id in enumerate(ids):
        out.append(
            {
                "id": _id,
                "text": docs[i],
                "metadata": metas[i],
                "distance": dists[i] if dists is not None else None,
            }
        )
    return out


def get_all_chunks(doc_id: str, limit: int = 5000) -> List[Dict]:
    coll = _collection()
    res = coll.get(where={"doc_id": doc_id}, limit=limit)
    out: List[Dict] = []
    if not res or not res.get("ids"):
        return out
    ids = res["ids"]
    docs = res["documents"]
    metas = res["metadatas"]
    pairs = list(zip(ids, docs, metas))
    pairs.sort(key=lambda x: x[2].get("chunk_index", 0))
    for _id, d, m in pairs:
        out.append({"id": _id, "text": d, "metadata": m})
    return out


def delete_doc(doc_id: str) -> None:
    coll = _collection()
    coll.delete(where={"doc_id": doc_id})
