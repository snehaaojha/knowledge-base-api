"""API routes for ingestion, search, and health."""

# Two ingest routes (/ingest and /ingest/document) are kept separate for API clarity:
# - /ingest uses "text" — common for direct paste, snippets, or API-to-API flows.
# - /ingest/document uses "content" — aligns with file-extraction workflows where
#   "content" denotes document body. Both delegate to the same service; schemas differ
#   only in field names to match caller expectations.
import asyncio
import logging

from fastapi import APIRouter, HTTPException, status

from app import db, embeddings, service
from app.schemas import (
    HealthResponse,
    IngestDocumentRequest,
    IngestResponse,
    IngestTextRequest,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_text(req: IngestTextRequest):
    """
    Ingest raw text. Chunks, embeds, and stores in the vector database.
    """
    try:
        result = await asyncio.to_thread(service.ingest_text, req.text, req.doc_id)
        return IngestResponse(
            doc_id=result["doc_id"],
            chunks_stored=result["chunks_stored"],
            message=f"Stored {result['chunks_stored']} chunks",
        )
    except Exception as e:
        logger.exception("Ingestion failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ingestion failed",
        )


@router.post("/ingest/document", response_model=IngestResponse)
async def ingest_document(req: IngestDocumentRequest):
    """
    Ingest document content. Same as /ingest but accepts 'content' field.
    """
    try:
        result = await asyncio.to_thread(service.ingest_text, req.content, req.doc_id)
        return IngestResponse(
            doc_id=result["doc_id"],
            chunks_stored=result["chunks_stored"],
            message=f"Stored {result['chunks_stored']} chunks",
        )
    except Exception as e:
        logger.exception("Document ingestion failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document ingestion failed",
        )


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    """
    Semantic search over ingested content. Returns top-k matches.
    """
    try:
        results = await asyncio.to_thread(service.search, req.query, req.top_k)
        return SearchResponse(
            query=req.query,
            results=[SearchResultItem(**r) for r in results],
            count=len(results),
        )
    except Exception as e:
        logger.exception("Search failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed",
        )


def _check_db() -> bool:
    """Sync DB check for use in thread."""
    try:
        db.ensure_index()
        return True
    except Exception as e:
        logger.warning("DB health check failed: %s", e)
        return False


def _check_embedding() -> bool:
    """Sync embedding check for use in thread."""
    try:
        embeddings.get_embedding_model()
        return True
    except Exception as e:
        logger.warning("Embedding health check failed: %s", e)
        return False


@router.get("/health", response_model=HealthResponse)
async def health():
    """
    Health check: verifies database and embedding model connectivity.
    Runs checks in thread pool to avoid blocking the event loop.
    """
    db_ok = await asyncio.to_thread(_check_db)
    embedding_ok = await asyncio.to_thread(_check_embedding)
    status_val = "healthy" if (db_ok and embedding_ok) else "degraded"
    return HealthResponse(status=status_val, db_ok=db_ok, embedding_ok=embedding_ok)
