"""API route tests. Mocks external dependencies (Endee, embeddings)."""

import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.exceptions import EmbeddingError, VectorStoreTimeoutError
from app.main import app


@pytest.fixture(autouse=True)
def mock_endee():
    """Mock Endee client at db layer for all tests."""
    with patch("app.db.get_endee_client") as mock_client:
        mock_index = MagicMock()
        mock_client.return_value.get_index.return_value = mock_index
        mock_client.return_value.list_indexes.return_value = []
        mock_client.return_value.create_index = MagicMock()
        yield mock_client, mock_index


@pytest.fixture(autouse=True)
def mock_embeddings():
    """Mock embedding generation at service layer (where it's used)."""
    fake_vector = [0.1] * 384

    def embed_texts_side_effect(texts):
        return [fake_vector for _ in texts]

    with patch("app.service.embed_texts") as mock_embed_texts:
        with patch("app.service.embed_single") as mock_embed_single:
            mock_embed_texts.side_effect = embed_texts_side_effect
            mock_embed_single.return_value = fake_vector
            yield mock_embed_texts, mock_embed_single


@patch("app.api.embeddings.get_embedding_model")
def test_health_returns_ok(mock_embed, client: TestClient, mock_endee):
    """Health endpoint returns status."""
    mock_client, _ = mock_endee[0], mock_endee[1]
    mock_client.return_value.list_indexes.return_value = [{"name": "knowledge_base"}]
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "db_ok" in data
    assert "embedding_ok" in data


def test_ingest_success(client: TestClient, mock_endee, mock_embeddings):
    """Successful ingestion returns doc_id and chunks_stored."""
    mock_index = mock_endee[1]
    resp = client.post("/api/v1/ingest", json={"text": "Hello world. This is a test document."})
    assert resp.status_code == 200
    data = resp.json()
    assert "doc_id" in data
    assert data["chunks_stored"] >= 1
    assert "message" in data
    mock_index.upsert.assert_called_once()


def test_ingest_empty_text_fails(client: TestClient):
    """Empty text returns 422."""
    resp = client.post("/api/v1/ingest", json={"text": ""})
    assert resp.status_code == 422


def test_ingest_missing_text_fails(client: TestClient):
    """Missing text field returns 422."""
    resp = client.post("/api/v1/ingest", json={})
    assert resp.status_code == 422


def test_ingest_invalid_doc_id_fails(client: TestClient, mock_endee, mock_embeddings):
    """doc_id with invalid chars (slash, dot) returns 422."""
    resp = client.post(
        "/api/v1/ingest",
        json={"text": "Hello world.", "doc_id": "invalid/id"},
    )
    assert resp.status_code == 422


def test_ingest_document_success(client: TestClient, mock_endee, mock_embeddings):
    """Document ingestion with content field works."""
    resp = client.post("/api/v1/ingest/document", json={"content": "Document content here."})
    assert resp.status_code == 200
    data = resp.json()
    assert "doc_id" in data
    assert data["chunks_stored"] >= 1


def test_search_success(client: TestClient, mock_endee, mock_embeddings):
    """Search returns results."""
    mock_index = mock_endee[1]
    mock_index.query.return_value = [
        {"id": "chunk1", "similarity": 0.9, "meta": {"text": "Relevant chunk"}},
    ]
    resp = client.post("/api/v1/search", json={"query": "find something", "top_k": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "find something"
    assert data["count"] >= 0
    assert "results" in data
    mock_index.query.assert_called_once()


def test_search_empty_query_fails(client: TestClient):
    """Empty query returns 422."""
    resp = client.post("/api/v1/search", json={"query": ""})
    assert resp.status_code == 422


def test_search_invalid_top_k_fails(client: TestClient):
    resp = client.post("/api/v1/search", json={"query": "test", "top_k": 100})
    assert resp.status_code == 422


def test_search_returns_empty_results(client: TestClient, mock_endee, mock_embeddings):
    mock_index = mock_endee[1]
    mock_index.query.return_value = []
    resp = client.post("/api/v1/search", json={"query": "nonexistent", "top_k": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"] == []
    assert data["count"] == 0


def test_ingest_returns_500_on_service_failure(client: TestClient, mock_endee, mock_embeddings):
    with patch("app.service.ingest_text") as mock_ingest:
        mock_ingest.side_effect = RuntimeError("DB unavailable")
        resp = client.post("/api/v1/ingest", json={"text": "Hello world."})
    assert resp.status_code == 500
    assert resp.json()["detail"] == "Ingestion failed"


def test_search_returns_500_on_service_failure(client: TestClient, mock_endee, mock_embeddings):
    with patch("app.service.search") as mock_search:
        mock_search.side_effect = RuntimeError("Embedding failed")
        resp = client.post("/api/v1/search", json={"query": "test", "top_k": 5})
    assert resp.status_code == 500
    assert resp.json()["detail"] == "Search failed"


def test_ingest_text_too_long_returns_422(client: TestClient):
    resp = client.post("/api/v1/ingest", json={"text": "x" * 1_000_001})
    assert resp.status_code == 422


def test_search_query_too_long_returns_422(client: TestClient):
    resp = client.post("/api/v1/search", json={"query": "x" * 10_001, "top_k": 5})
    assert resp.status_code == 422


def test_root_returns_message(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "message" in resp.json()


def test_response_includes_request_id(client: TestClient):
    resp = client.get("/")
    assert "X-Request-ID" in resp.headers
    assert len(resp.headers["X-Request-ID"]) > 0


def test_request_id_from_header_propagated(client: TestClient):
    resp = client.get("/", headers={"X-Request-ID": "custom-id-123"})
    assert resp.headers["X-Request-ID"] == "custom-id-123"


def test_validation_error_returns_422_with_detail(client: TestClient):
    """Validation errors return 422 with structured detail."""
    resp = client.post("/api/v1/ingest", json={"text": "", "doc_id": "x"})
    assert resp.status_code == 422
    data = resp.json()
    assert "detail" in data
    assert "message" in data or "detail" in data


def test_ingest_returns_504_on_timeout(client: TestClient, mock_endee, mock_embeddings):
    """Vector store timeout returns 504 Gateway Timeout."""
    with patch("app.service.ingest_text") as mock_ingest:
        mock_ingest.side_effect = VectorStoreTimeoutError("timed out")
        resp = client.post("/api/v1/ingest", json={"text": "Hello world."})
    assert resp.status_code == 504
    detail = resp.json().get("detail", "")
    assert "timeout" in detail.lower() or "timed out" in detail.lower()


def test_search_returns_504_on_timeout(client: TestClient, mock_endee, mock_embeddings):
    """Vector store timeout on search returns 504."""
    with patch("app.service.search") as mock_search:
        mock_search.side_effect = VectorStoreTimeoutError("timed out")
        resp = client.post("/api/v1/search", json={"query": "test", "top_k": 5})
    assert resp.status_code == 504
