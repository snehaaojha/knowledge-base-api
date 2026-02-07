"""Vector database operations using Endee."""

import concurrent.futures
import logging
import threading
import uuid
from typing import Any, Callable, TypeVar

from endee import Endee, Precision

from app.config import settings
from app.exceptions import VectorStoreError, VectorStoreTimeoutError

T = TypeVar("T")


def _with_timeout(func: Callable[[], T], timeout_seconds: int | None = None) -> T:
    """Run a sync callable with a timeout to avoid hanging on Endee failures."""
    timeout = timeout_seconds if timeout_seconds is not None else settings.endee_timeout_seconds
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(func)
            return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError as e:
        raise VectorStoreTimeoutError(f"Endee operation timed out after {timeout}s") from e

logger = logging.getLogger(__name__)

_client: Endee | None = None
_client_lock = threading.Lock()
_index_ensured = False
_index_lock = threading.Lock()


def get_endee_client() -> Endee:
    """Create or return the Endee client. Single instance per process. Thread-safe."""
    global _client
    if _client is not None:
        return _client
    with _client_lock:
        if _client is not None:
            return _client
        token = settings.endee_token or None
        _client = Endee(token=token) if token else Endee()
        if settings.endee_base_url:
            _client.set_base_url(settings.endee_base_url)
        return _client


def ensure_index() -> None:
    """Create the index if it does not exist. Cached after first success."""
    global _index_ensured
    if _index_ensured:
        return
    with _index_lock:
        if _index_ensured:
            return
        _ensure_index_impl()
        _index_ensured = True


def _ensure_index_impl() -> None:
    """Internal: actually create index if missing."""

    def _do() -> None:
        client = get_endee_client()
        indexes = client.list_indexes() or []
        index_names = [
            (idx.get("name") if isinstance(idx, dict) else str(idx))
            for idx in indexes if idx is not None
        ]
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

    try:
        _with_timeout(_do)
    except VectorStoreTimeoutError:
        raise
    except Exception as e:
        logger.error("Failed to ensure index: %s", e)
        raise VectorStoreError(f"Failed to ensure index: {e}") from e


def get_index() -> Any:
    """Return the Endee index for upsert and query."""
    ensure_index()

    def _do() -> Any:
        return get_endee_client().get_index(name=settings.index_name)

    try:
        return _with_timeout(_do)
    except VectorStoreTimeoutError:
        raise
    except Exception as e:
        logger.error("get_index failed: %s", e)
        raise VectorStoreError(f"get_index failed: {e}") from e


def upsert_vectors(items: list[dict[str, Any]]) -> None:
    """Insert or update vectors in the index. Each item: id, vector, meta."""
    index = get_index()

    def _do() -> None:
        index.upsert(items)

    try:
        _with_timeout(_do)
    except VectorStoreTimeoutError:
        raise
    except Exception as e:
        logger.error("Upsert failed: %s", e)
        raise VectorStoreError(f"Upsert failed: {e}") from e
    logger.info("Upserted %d vectors to index %s", len(items), settings.index_name)


def query_vectors(vector: list[float], top_k: int = 5) -> list[dict[str, Any]]:
    """Search for similar vectors. Returns list of dicts with id, similarity, meta."""
    index = get_index()

    def _do() -> list[dict[str, Any]]:
        results = index.query(vector=vector, top_k=top_k)
        return list(results) if results else []

    try:
        return _with_timeout(_do)
    except VectorStoreTimeoutError:
        raise
    except Exception as e:
        logger.error("Query failed: %s", e)
        raise VectorStoreError(f"Query failed: {e}") from e


def generate_chunk_id(doc_id: str, chunk_index: int) -> str:
    """Generate a unique id for a chunk."""
    return f"{doc_id}_{chunk_index}_{uuid.uuid4().hex[:8]}"
