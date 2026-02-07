"""Embedding generation for text. Uses sentence-transformers locally."""

import logging
import threading
from typing import TYPE_CHECKING

from app.config import settings

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
    return [v.tolist() for v in vectors]


def embed_single(text: str) -> list[float]:
    """Generate embedding for a single text."""
    if not text or not text.strip():
        raise ValueError("Text must be non-empty")
    vectors = embed_texts([text])
    if not vectors:
        raise ValueError("Embedding failed")
    return vectors[0]
