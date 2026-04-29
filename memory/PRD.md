# DocuSense AI — PRD

## Original Problem Statement
Build a production-ready Generative AI project named **DocuSense AI — Intelligent Research & Synthesis Engine**: a RAG system to ingest PDFs/text, run semantic search, and answer questions with citations. Frontend in Streamlit, backend in FastAPI, vector DB in FAISS/Chroma, LLM via OpenAI/HuggingFace. Must include at least two advanced features (multi-doc chat, comparison, contradictions, NER, vision).

## User Choices (2026-04-29)
- Frontend: **Streamlit**
- LLM: **Gemini 3 Flash** via **Emergent Universal Key** (emergentintegrations)
- Embeddings: **Local HuggingFace** `sentence-transformers/all-MiniLM-L6-v2`
- Vector DB: **ChromaDB** persistent at `/app/data/chroma`
- Advanced features: **Multi-document chat**, **Compare two documents**, **Highlight contradictions**

## Architecture
- **Backend** FastAPI (port 8001, `/api` prefix)
  - `services/pdf_service.py` — pypdf extraction + word-overlap chunking (900/150)
  - `services/embedding_service.py` — sentence-transformers, normalized
  - `services/vector_store.py` — Chroma cosine, single collection w/ `doc_id` metadata filter
  - `services/llm_service.py` — Gemini 3 Flash via emergentintegrations
  - `routes/documents.py` — `/upload`, `/documents`, `/documents/{id}` (DELETE)
  - `routes/rag.py` — `/query`, `/summary`, `/insights`, `/compare`, `/contradictions`
- **Frontend** Streamlit (port 3000) — repurposed `yarn start` to launch streamlit
  - Sidebar: upload + library + multi-select scope
  - Tabs: Chat (with citations) | Summary | Insights (JSON-rendered + entities) | Compare | Contradictions
  - Custom dark navy + amber theme, JetBrains Mono headings

## Persona
- Researchers, analysts, lawyers, product managers needing fast cross-document Q&A with traceable sources.

## Implemented (2026-04-29)
- PDF/TXT/MD ingestion, chunking, embedding, persistent Chroma store
- RAG Q&A with inline `[Source N]` citations and source chunk reveal
- Multi-document chat via `doc_ids[]` scope filter
- Document summary (Overview / Key Points / Conclusion)
- Insights extraction (JSON insights with page refs + entities)
- Compare two documents (Common Ground / Differences / Unique to A / B / Verdict)
- Contradictions detection between two documents
- Streamlit UI with session-state chat history, KPI cards, dark theme
- Backend tests: 16/16 passing (100%)

## Backlog
- **P1** Streaming token responses (SSE) for chat
- **P1** Highlight specific contradicting passages in original PDF
- **P2** Vision/chart understanding for image-rich PDFs
- **P2** Per-document chat namespaces & history persistence in MongoDB
- **P2** Export chat or insights to markdown / PDF
- **P3** Auth + per-user document libraries

## Files
- `/app/backend/server.py`, `/app/backend/routes/*`, `/app/backend/services/*`
- `/app/frontend/app.py`, `/app/frontend/.streamlit/config.toml`
- `/app/data/chroma`, `/app/data/uploads`
- `/app/backend/tests/backend_test.py`
