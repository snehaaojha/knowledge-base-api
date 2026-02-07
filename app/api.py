"""API routes for ingestion, search, and health."""

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
def ingest_text(req: IngestTextRequest):
    """
    Ingest raw text. Chunks, embeds, and stores in the vector database.
    """
    try:
        result = service.ingest_text(req.text, req.doc_id)
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
def ingest_document(req: IngestDocumentRequest):
    """
    Ingest document content. Same as /ingest but accepts 'content' field.
    """
    try:
        result = service.ingest_text(req.content, req.doc_id)
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
def search(req: SearchRequest):
    """
    Semantic search over ingested content. Returns top-k matches.
    """
    try:
        results = service.search(req.query, req.top_k)
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


@router.get("/health", response_model=HealthResponse)
def health():
    """
    Health check: verifies database and embedding model connectivity.
    """
    db_ok = False
    embedding_ok = False
    try:
        db.ensure_index()
        db_ok = True
    except Exception as e:
        logger.warning("DB health check failed: %s", e)
    try:
        embeddings.get_embedding_model()
        embedding_ok = True
    except Exception as e:
        logger.warning("Embedding health check failed: %s", e)
    status_val = "healthy" if (db_ok and embedding_ok) else "degraded"
    return HealthResponse(status=status_val, db_ok=db_ok, embedding_ok=embedding_ok)
