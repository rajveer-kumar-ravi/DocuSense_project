"""RAG endpoints: query, summary, insights, compare, contradictions."""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from services.embedding_service import embed_query
from services.llm_service import ask
from services.vector_store import get_all_chunks, query

log = logging.getLogger(__name__)
router = APIRouter()


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    doc_ids: Optional[List[str]] = None
    top_k: int = 6


class Citation(BaseModel):
    doc_id: str
    doc_name: str
    page: int
    chunk_index: int
    text: str
    score: Optional[float] = None


class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation]


class DocIdRequest(BaseModel):
    doc_id: str


class CompareRequest(BaseModel):
    doc_id_a: str
    doc_id_b: str


def _format_context(hits: List[dict]) -> str:
    blocks = []
    for i, h in enumerate(hits, start=1):
        m = h["metadata"]
        blocks.append(
            f"[Source {i}] (doc: {m.get('doc_name')}, page {m.get('page')})\n{h['text']}"
        )
    return "\n\n".join(blocks)


def _truncate_chunks(chunks: List[dict], max_chars: int = 18000) -> str:
    parts: List[str] = []
    total = 0
    for c in chunks:
        m = c["metadata"]
        block = f"[p.{m.get('page')}] {c['text']}"
        if total + len(block) > max_chars:
            break
        parts.append(block)
        total += len(block) + 2
    return "\n\n".join(parts)


def _build_router(db: AsyncIOMotorDatabase) -> APIRouter:

    async def _doc_name(doc_id: str) -> str:
        meta = await db.documents.find_one({"id": doc_id}, {"_id": 0, "name": 1})
        if not meta:
            raise HTTPException(404, f"Document {doc_id} not found")
        return meta["name"]

    @router.post("/query", response_model=QueryResponse)
    async def query_endpoint(req: QueryRequest) -> QueryResponse:
        try:
            qvec = embed_query(req.question)
        except Exception as exc:
            log.exception("Embedding failed")
            raise HTTPException(500, f"Embedding failed: {exc}") from exc

        hits = query(qvec, doc_ids=req.doc_ids, top_k=req.top_k)
        if not hits:
            return QueryResponse(
                answer="I couldn't find anything relevant in the selected documents.",
                citations=[],
            )

        context = _format_context(hits)
        system = (
            "You are DocuSense AI, a careful research assistant. "
            "Answer ONLY using the supplied sources. "
            "Quote facts faithfully and cite sources inline as [Source N]. "
            "If the answer is not in the sources, reply: 'The provided documents do not contain this information.' "
            "Be concise and direct."
        )
        user = f"Question: {req.question}\n\nSources:\n{context}\n\nAnswer with inline [Source N] citations."
        try:
            answer = await ask(system, user)
        except Exception as exc:
            log.exception("LLM call failed")
            raise HTTPException(502, f"LLM error: {exc}") from exc

        citations = [
            Citation(
                doc_id=h["metadata"]["doc_id"],
                doc_name=h["metadata"]["doc_name"],
                page=int(h["metadata"]["page"]),
                chunk_index=int(h["metadata"]["chunk_index"]),
                text=h["text"],
                score=(1 - h["distance"]) if h.get("distance") is not None else None,
            )
            for h in hits
        ]
        return QueryResponse(answer=answer, citations=citations)

    @router.post("/summary")
    async def summary_endpoint(req: DocIdRequest) -> dict:
        await _doc_name(req.doc_id)
        chunks = get_all_chunks(req.doc_id)
        if not chunks:
            raise HTTPException(404, "No content found for this document")
        body = _truncate_chunks(chunks)
        system = (
            "You are DocuSense AI. Produce a clear, structured summary of the document. "
            "Output 3 sections: 'Overview' (3-4 sentences), 'Key Points' (5-8 bullets), and 'Conclusion' (2-3 sentences). "
            "Stay strictly faithful to the document."
        )
        try:
            text = await ask(system, f"Document content:\n\n{body}")
        except Exception as exc:
            log.exception("Summary failed")
            raise HTTPException(502, f"LLM error: {exc}") from exc
        return {"doc_id": req.doc_id, "summary": text}

    @router.post("/insights")
    async def insights_endpoint(req: DocIdRequest) -> dict:
        await _doc_name(req.doc_id)
        chunks = get_all_chunks(req.doc_id)
        if not chunks:
            raise HTTPException(404, "No content found for this document")
        body = _truncate_chunks(chunks)
        system = (
            "You are DocuSense AI, an analyst. Extract the most actionable, non-obvious insights "
            "from the document. Output ONLY a JSON object with this shape: "
            '{"insights":[{"title":"...","detail":"...","page":N}], "entities":{"people":[],"orgs":[],"places":[],"dates":[]}} '
            "Limit to 6-10 insights. The 'page' must be an integer page number from the source."
        )
        try:
            text = await ask(system, f"Document content:\n\n{body}")
        except Exception as exc:
            log.exception("Insights failed")
            raise HTTPException(502, f"LLM error: {exc}") from exc
        return {"doc_id": req.doc_id, "raw": text}

    @router.post("/compare")
    async def compare_endpoint(req: CompareRequest) -> dict:
        if req.doc_id_a == req.doc_id_b:
            raise HTTPException(400, "Pick two different documents")
        name_a = await _doc_name(req.doc_id_a)
        name_b = await _doc_name(req.doc_id_b)
        a_chunks = get_all_chunks(req.doc_id_a)
        b_chunks = get_all_chunks(req.doc_id_b)
        if not a_chunks or not b_chunks:
            raise HTTPException(404, "One of the documents has no content")
        body_a = _truncate_chunks(a_chunks, max_chars=8500)
        body_b = _truncate_chunks(b_chunks, max_chars=8500)
        system = (
            "You are DocuSense AI. Compare two documents and write a structured comparison. "
            "Use these sections in markdown: '## Common Ground', '## Differences', "
            "'## Unique to A', '## Unique to B', '## Verdict'. Be specific and cite page numbers like (p.3) "
            "when referencing a document. Stay faithful to the texts."
        )
        user = f"Document A — {name_a}:\n{body_a}\n\nDocument B — {name_b}:\n{body_b}"
        try:
            text = await ask(system, user)
        except Exception as exc:
            log.exception("Compare failed")
            raise HTTPException(502, f"LLM error: {exc}") from exc
        return {
            "doc_a": {"id": req.doc_id_a, "name": name_a},
            "doc_b": {"id": req.doc_id_b, "name": name_b},
            "comparison": text,
        }

    @router.post("/contradictions")
    async def contradictions_endpoint(req: CompareRequest) -> dict:
        if req.doc_id_a == req.doc_id_b:
            raise HTTPException(400, "Pick two different documents")
        name_a = await _doc_name(req.doc_id_a)
        name_b = await _doc_name(req.doc_id_b)
        a_chunks = get_all_chunks(req.doc_id_a)
        b_chunks = get_all_chunks(req.doc_id_b)
        if not a_chunks or not b_chunks:
            raise HTTPException(404, "One of the documents has no content")
        body_a = _truncate_chunks(a_chunks, max_chars=8500)
        body_b = _truncate_chunks(b_chunks, max_chars=8500)
        system = (
            "You are DocuSense AI, a fact-check analyst. Identify factual or claim-level CONTRADICTIONS "
            "between the two documents. For each contradiction, output a markdown bullet of the form: "
            "- **<Topic>** — A says: \"<quote or paraphrase>\" (p.X). B says: \"<quote or paraphrase>\" (p.Y). "
            "Then a one-line note on the conflict. "
            "If no clear contradictions exist, write: 'No direct contradictions found.' Do not fabricate."
        )
        user = f"Document A — {name_a}:\n{body_a}\n\nDocument B — {name_b}:\n{body_b}"
        try:
            text = await ask(system, user)
        except Exception as exc:
            log.exception("Contradictions failed")
            raise HTTPException(502, f"LLM error: {exc}") from exc
        return {
            "doc_a": {"id": req.doc_id_a, "name": name_a},
            "doc_b": {"id": req.doc_id_b, "name": name_b},
            "contradictions": text,
        }

    return router


def get_router(db: AsyncIOMotorDatabase) -> APIRouter:
    return _build_router(db)
