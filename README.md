# DocuSense AI — Intelligent Research & Synthesis Engine

Production-ready Retrieval-Augmented Generation (RAG) app to chat with your PDF/text
documents, get summaries, extract insights, compare two documents, and surface
contradictions — all with cited sources.

## Stack
- **Backend**: FastAPI + Motor (MongoDB) + ChromaDB + sentence-transformers
- **Frontend**: Streamlit
- **LLM**: Gemini 3 Flash via Emergent Universal Key (`emergentintegrations`)
- **Embeddings**: local `sentence-transformers/all-MiniLM-L6-v2`

## Project Structure
```
docusense-ai/
├── backend/
│   ├── server.py
│   ├── routes/
│   │   ├── documents.py
│   │   └── rag.py
│   ├── services/
│   │   ├── pdf_service.py
│   │   ├── embedding_service.py
│   │   ├── vector_store.py
│   │   └── llm_service.py
│   ├── tests/backend_test.py
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── app.py
│   └── .streamlit/config.toml
├── memory/PRD.md
└── README.md
```

## Local Setup

### 1. Prereqs
- Python 3.11+
- MongoDB running on `mongodb://localhost:27017`
  (or change `MONGO_URL` in `.env`)

### 2. Install dependencies
```bash
cd docusense-ai
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ \
            -r backend/requirements.txt
pip install streamlit requests
```

### 3. Configure environment
```bash
cp backend/.env.example backend/.env
# Edit backend/.env — set EMERGENT_LLM_KEY (or your own provider key)
```
Required vars:
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=docusense
CORS_ORIGINS=*
EMERGENT_LLM_KEY=sk-emergent-xxxxxxxxxxxx
CHROMA_DIR=./data/chroma
UPLOAD_DIR=./data/uploads
EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2
GEMINI_MODEL=gemini-3-flash-preview
```

### 4. Run the backend
```bash
cd backend
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```
Health check: http://localhost:8001/api/health

### 5. Run the frontend (in a second terminal)
```bash
cd frontend
DOCUSENSE_API=http://localhost:8001/api streamlit run app.py
```
Open: http://localhost:8501

## API Endpoints
| Method | Path | Body | Purpose |
|---|---|---|---|
| GET  | `/api/health`             | — | Service health |
| POST | `/api/upload`             | multipart `file` | Ingest PDF/TXT/MD |
| GET  | `/api/documents`          | — | List ingested docs |
| DELETE | `/api/documents/{id}`   | — | Remove doc + chunks |
| POST | `/api/query`              | `{question, doc_ids?, top_k?}` | RAG Q&A with citations |
| POST | `/api/summary`            | `{doc_id}` | Structured summary |
| POST | `/api/insights`           | `{doc_id}` | JSON insights + entities |
| POST | `/api/compare`            | `{doc_id_a, doc_id_b}` | Comparison markdown |
| POST | `/api/contradictions`     | `{doc_id_a, doc_id_b}` | Contradiction list |

## Tests
```bash
cd backend && pytest tests/
```
