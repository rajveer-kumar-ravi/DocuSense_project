"""PDF / text extraction + chunking utilities."""
from __future__ import annotations

import io
import re
from typing import List, Tuple

from pypdf import PdfReader


def extract_text(file_bytes: bytes, filename: str) -> List[Tuple[int, str]]:
    """Return list of (page_number, page_text). For txt files page=1."""
    name = filename.lower()
    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(file_bytes))
        pages: List[Tuple[int, str]] = []
        for idx, page in enumerate(reader.pages, start=1):
            try:
                txt = page.extract_text() or ""
            except Exception:
                txt = ""
            pages.append((idx, txt))
        return pages
    # text-like
    text = file_bytes.decode("utf-8", errors="ignore")
    return [(1, text)]


_WS = re.compile(r"\s+")


def _clean(t: str) -> str:
    return _WS.sub(" ", t).strip()


def chunk_pages(
    pages: List[Tuple[int, str]],
    chunk_size: int = 900,
    overlap: int = 150,
) -> List[dict]:
    """Word-based chunking with overlap, preserving source page numbers.

    Returns list of dicts: {chunk_index, page, text}
    """
    chunks: List[dict] = []
    chunk_idx = 0
    for page_num, page_text in pages:
        words = _clean(page_text).split()
        if not words:
            continue
        step = max(1, chunk_size - overlap)
        i = 0
        while i < len(words):
            window = words[i : i + chunk_size]
            text = " ".join(window)
            if text:
                chunks.append(
                    {"chunk_index": chunk_idx, "page": page_num, "text": text}
                )
                chunk_idx += 1
            if i + chunk_size >= len(words):
                break
            i += step
    return chunks
