"""Business logic: chunking, orchestration of ingestion and search."""

import logging
import re
import uuid

from app.config import settings
from app.db import generate_chunk_id, query_vectors, upsert_vectors
from app.embeddings import embed_single, embed_texts

logger = logging.getLogger(__name__)


def chunk_text_sentences(text: str, chunk_size: int | None = None) -> list[str]:
    """
    Split text by sentences when possible, then by size.
    More natural than pure character splitting.
    """
    size = chunk_size or settings.chunk_size
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if not sentences:
        return [text.strip()] if text.strip() else []
    chunks = []
    current = []
    current_len = 0
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if current_len + len(s) + 1 <= size or not current:
            current.append(s)
            current_len += len(s) + 1
        else:
            if current:
                chunks.append(" ".join(current))
            current = [s]
            current_len = len(s) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


def ingest_text(text: str, doc_id: str | None = None) -> dict:
    """
    Ingest text: chunk, embed, store in Endee.
    Returns {doc_id, chunks_stored}.
    """
    doc_id = doc_id or str(uuid.uuid4())
    chunks = chunk_text_sentences(text)
    if not chunks:
        return {"doc_id": doc_id, "chunks_stored": 0}
    logger.info("Ingestion started for doc_id=%s, chunks=%d", doc_id, len(chunks))
    vectors = embed_texts(chunks)
    items = []
    for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
        cid = generate_chunk_id(doc_id, i)
        items.append({
            "id": cid,
            "vector": vec,
            "meta": {"text": chunk, "doc_id": doc_id, "chunk_index": i},
        })
    upsert_vectors(items)
    logger.info("Ingestion completed for doc_id=%s, chunks_stored=%d", doc_id, len(items))
    return {"doc_id": doc_id, "chunks_stored": len(items)}


def search(query: str, top_k: int = 5) -> list[dict]:
    """
    Search: embed query, retrieve top-k, return structured results.
    """
    top_k = min(top_k, settings.max_top_k)
    logger.info("Search started: query=%r, top_k=%d", query[:50], top_k)
    query_vector = embed_single(query)
    raw = query_vectors(vector=query_vector, top_k=top_k)
    results = []
    for r in raw:
        meta = r.get("meta") or {}
        text = meta.get("text", "")
        results.append({
            "id": r.get("id", ""),
            "score": float(r.get("similarity", 0.0)),
            "text": text,
            "meta": meta,
        })
    logger.info("Search completed: found %d results", len(results))
    return results
