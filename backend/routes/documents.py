"""Document ingest / list / delete endpoints."""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from services.embedding_service import embed_texts
from services.pdf_service import chunk_pages, extract_text
from services.vector_store import add_chunks, delete_doc

log = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_EXT = {".pdf", ".txt", ".md"}


class DocumentOut(BaseModel):
    id: str
    name: str
    num_chunks: int
    num_pages: int
    size_bytes: int
    uploaded_at: str


def _build_router(db: AsyncIOMotorDatabase) -> APIRouter:
    upload_dir = Path(os.environ.get("UPLOAD_DIR", "/app/data/uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)

    @router.post("/upload", response_model=DocumentOut)
    async def upload(file: UploadFile = File(...)) -> DocumentOut:
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_EXT:
            raise HTTPException(400, f"Unsupported file type: {ext}. Allowed: {sorted(ALLOWED_EXT)}")
        content = await file.read()
        if not content:
            raise HTTPException(400, "Empty file")
        if len(content) > 25 * 1024 * 1024:
            raise HTTPException(413, "File too large (max 25 MB)")

        doc_id = str(uuid.uuid4())
        safe_name = file.filename or f"document{ext}"
        saved_path = upload_dir / f"{doc_id}{ext}"
        saved_path.write_bytes(content)

        try:
            pages = extract_text(content, safe_name)
            chunks = chunk_pages(pages)
            if not chunks:
                raise HTTPException(422, "Could not extract any text from this document.")
            embeddings = embed_texts([c["text"] for c in chunks])
            add_chunks(doc_id=doc_id, doc_name=safe_name, chunks=chunks, embeddings=embeddings)
        except HTTPException:
            saved_path.unlink(missing_ok=True)
            raise
        except Exception as exc:
            log.exception("Ingestion failure for %s", safe_name)
            saved_path.unlink(missing_ok=True)
            raise HTTPException(500, f"Failed to ingest document: {exc}") from exc

        meta = {
            "id": doc_id,
            "name": safe_name,
            "num_chunks": len(chunks),
            "num_pages": len(pages),
            "size_bytes": len(content),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "path": str(saved_path),
        }
        await db.documents.insert_one(dict(meta))
        return DocumentOut(**{k: meta[k] for k in DocumentOut.model_fields})

    @router.get("/documents", response_model=List[DocumentOut])
    async def list_documents() -> List[DocumentOut]:
        cur = db.documents.find({}, {"_id": 0}).sort("uploaded_at", -1)
        items = await cur.to_list(500)
        return [DocumentOut(**{k: it[k] for k in DocumentOut.model_fields if k in it}) for it in items]

    @router.delete("/documents/{doc_id}")
    async def delete_document(doc_id: str) -> dict:
        meta = await db.documents.find_one({"id": doc_id}, {"_id": 0})
        if not meta:
            raise HTTPException(404, "Document not found")
        try:
            delete_doc(doc_id)
        except Exception:
            log.exception("Vector delete failed for %s", doc_id)
        if meta.get("path"):
            try:
                Path(meta["path"]).unlink(missing_ok=True)
            except Exception:
                pass
        await db.documents.delete_one({"id": doc_id})
        return {"ok": True, "id": doc_id}

    return router


def get_router(db: AsyncIOMotorDatabase) -> APIRouter:
    return _build_router(db)
