"""Application-specific exceptions for clearer error handling."""


class ServiceError(Exception):
    """Base for service-layer errors (ingestion, search)."""


class EmbeddingError(ServiceError):
    """Embedding generation failed."""


class VectorStoreError(ServiceError):
    """Vector database operation failed."""


class VectorStoreTimeoutError(VectorStoreError):
    """Vector database call timed out."""
