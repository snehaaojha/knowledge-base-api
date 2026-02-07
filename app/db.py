"""Vector database operations using Endee."""

import logging
import uuid
from typing import Any

from endee import Endee, Precision

from app.config import settings

logger = logging.getLogger(__name__)

_client: Endee | None = None


def get_endee_client() -> Endee:
    """Create or return the Endee client. Single instance per process."""
    global _client
    if _client is None:
        token = settings.endee_token or None
        _client = Endee(token=token) if token else Endee()
        if settings.endee_base_url:
            _client.set_base_url(settings.endee_base_url)
    return _client


def ensure_index() -> None:
    """Create the index if it does not exist."""
    client = get_endee_client()
    try:
        indexes = client.list_indexes() or []
        index_names = [idx.get("name") if isinstance(idx, dict) else str(idx) for idx in indexes]
        if settings.index_name not in index_names:
            client.create_index(
                name=settings.index_name,
                dimension=settings.embedding_dimension,
                space_type="cosine",
                precision=Precision.INT8D,
            )
            logger.info("Created index: %s", settings.index_name)
        else:
            logger.debug("Index already exists: %s", settings.index_name)
    except Exception as e:
        logger.error("Failed to ensure index: %s", e)
        raise


def get_index():
    """Return the Endee index for upsert and query."""
    ensure_index()
    return get_endee_client().get_index(name=settings.index_name)


def upsert_vectors(items: list[dict[str, Any]]) -> None:
    """Insert or update vectors in the index. Each item: id, vector, meta."""
    index = get_index()
    index.upsert(items)
    logger.info("Upserted %d vectors to index %s", len(items), settings.index_name)


def query_vectors(vector: list[float], top_k: int = 5) -> list[dict[str, Any]]:
    """Search for similar vectors. Returns list of dicts with id, similarity, meta."""
    index = get_index()
    results = index.query(vector=vector, top_k=top_k)
    return list(results) if results else []


def generate_chunk_id(doc_id: str, chunk_index: int) -> str:
    """Generate a unique id for a chunk."""
    return f"{doc_id}_{chunk_index}_{uuid.uuid4().hex[:8]}"
