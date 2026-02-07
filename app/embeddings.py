"""Embedding generation for text. Uses sentence-transformers locally."""

import logging
import threading
from typing import TYPE_CHECKING

from app.config import settings
from app.exceptions import EmbeddingError

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_model: "SentenceTransformer | None" = None
_model_lock = threading.Lock()


def get_embedding_model() -> "SentenceTransformer":
    """Lazy-load the embedding model. Single instance for the process. Thread-safe."""
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        from sentence_transformers import SentenceTransformer
        logger.info("Loading embedding model: %s", settings.embedding_model)
        _model = SentenceTransformer(settings.embedding_model)
        return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of texts.
    Returns list of vectors, each of dimension embedding_dimension.
    """
    if not texts:
        return []
    model = get_embedding_model()
    vectors = model.encode(texts, convert_to_numpy=True)
    result = [v.tolist() for v in vectors]
    for i, vec in enumerate(result):
        if len(vec) != settings.embedding_dimension:
            raise EmbeddingError(
                f"Chunk {i}: unexpected dimension {len(vec)}, expected {settings.embedding_dimension}"
            )
    return result


def embed_single(text: str) -> list[float]:
    """Generate embedding for a single text."""
    if not text or not text.strip():
        raise EmbeddingError("Text must be non-empty")
    vectors = embed_texts([text])
    if not vectors:
        raise EmbeddingError("Embedding failed")
    vec = vectors[0]
    if len(vec) != settings.embedding_dimension:
        raise EmbeddingError(
            f"Unexpected dimension: got {len(vec)}, expected {settings.embedding_dimension}"
        )
    return vec
