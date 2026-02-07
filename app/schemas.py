"""Request and response models for the API."""

from pydantic import BaseModel, Field


class IngestTextRequest(BaseModel):
    """Payload for ingesting raw text."""

    text: str = Field(..., min_length=1, max_length=1_000_000, description="Text content to ingest")
    doc_id: str | None = Field(None, max_length=256, description="Optional document identifier")


class IngestDocumentRequest(BaseModel):
    """Payload for ingesting document content (same as text, semantically)."""

    content: str = Field(..., min_length=1, max_length=1_000_000, description="Document content to ingest")
    doc_id: str | None = Field(None, max_length=256, description="Optional document identifier")


class SearchRequest(BaseModel):
    """Payload for semantic search."""

    query: str = Field(..., min_length=1, max_length=10_000, description="Search query")
    top_k: int = Field(5, ge=1, le=50, description="Number of results to return")


class SearchResultItem(BaseModel):
    """Single search result with id, score, and text."""

    id: str
    score: float
    text: str
    meta: dict = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Response containing search results."""

    query: str
    results: list[SearchResultItem]
    count: int


class IngestResponse(BaseModel):
    """Response after successful ingestion."""

    doc_id: str
    chunks_stored: int
    message: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    db_ok: bool
    embedding_ok: bool
