"""DocuSense AI — FastAPI entry point."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
log = logging.getLogger("docusense")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="DocuSense AI", version="1.0.0")
api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root() -> dict:
    return {"name": "DocuSense AI", "status": "ok"}


@api_router.get("/health")
async def health() -> dict:
    try:
        await db.command("ping")
        mongo_ok = True
    except Exception:
        mongo_ok = False
    return {
        "ok": True,
        "mongo": mongo_ok,
        "llm_key": bool(os.environ.get("EMERGENT_LLM_KEY")),
    }


# Mount feature routers
from routes.documents import get_router as documents_router  # noqa: E402
# from routes.rag import get_router as rag_router  # noqa: E402

api_router.include_router(documents_router(db))
# api_router.include_router(rag_router(db))

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client() -> None:
    client.close()


@app.on_event("startup")
async def startup_event() -> None:
    log.info("DocuSense AI starting up")
    Path(os.environ.get("UPLOAD_DIR", "/app/data/uploads")).mkdir(parents=True, exist_ok=True)
    Path(os.environ.get("CHROMA_DIR", "/app/data/chroma")).mkdir(parents=True, exist_ok=True)
