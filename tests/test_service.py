"""Service layer tests."""

import pytest
from unittest.mock import patch

from app.service import chunk_text_sentences, ingest_text, search


def test_chunk_text_sentences_empty():
    assert chunk_text_sentences("") == []
    assert chunk_text_sentences("   ") == []


def test_chunk_text_sentences_single():
    text = "This is a sentence."
    chunks = chunk_text_sentences(text, chunk_size=100)
    assert len(chunks) == 1
    assert "sentence" in chunks[0]


def test_chunk_text_sentences_splits_long_text():
    text = "First sentence here. " + "Second part. " * 30 + "Final sentence."
    chunks = chunk_text_sentences(text, chunk_size=50)
    assert len(chunks) >= 2


def test_chunk_text_sentences_caps_long_single_sentence():
    """Very long sentence without period is split by max chunk size."""
    text = "A" * 1000 + "B" * 500  # No sentence boundary
    chunks = chunk_text_sentences(text, chunk_size=100)
    assert len(chunks) >= 2
    assert all(len(c) <= 512 for c in chunks)


def test_sanitize_meta_handles_circular_ref():
    """_sanitize_meta does not recurse infinitely on circular refs."""
    from app.service import _sanitize_meta
    d = {}
    d["self"] = d
    result = _sanitize_meta(d)
    assert result == {"self": "[cyclic]"}


@patch("app.service.upsert_vectors")
@patch("app.service.embed_texts")
@patch("app.service.chunk_text_sentences")
def test_ingest_text_mocked(chunk_mock, embed_mock, upsert_mock):
    """Ingestion orchestrates chunking, embedding, and upsert."""
    chunk_mock.return_value = ["chunk one", "chunk two"]
    embed_mock.return_value = [[0.1] * 384, [0.2] * 384]
    result = ingest_text("Some text.", doc_id="doc1")
    assert result["doc_id"] == "doc1"
    assert result["chunks_stored"] == 2
    embed_mock.assert_called_once_with(["chunk one", "chunk two"])
    upsert_mock.assert_called_once()
    items = upsert_mock.call_args[0][0]
    assert len(items) == 2
    assert all("id" in x and "vector" in x and "meta" in x for x in items)


@patch("app.service.query_vectors")
@patch("app.service.embed_single")
def test_search_mocked(embed_mock, query_mock):
    """Search orchestrates embedding and query."""
    embed_mock.return_value = [0.1] * 384
    query_mock.return_value = [
        {"id": "c1", "similarity": 0.95, "meta": {"text": "match"}},
    ]
    results = search("test query", top_k=3)
    assert len(results) == 1
    assert results[0]["id"] == "c1"
    assert results[0]["score"] == 0.95
    assert results[0]["text"] == "match"


def test_ingest_raises_on_embedding_count_mismatch():
    """Ingest raises EmbeddingError when embed_texts returns wrong count."""
    from app.exceptions import EmbeddingError

    with patch("app.service.embed_texts") as embed_mock:
        embed_mock.return_value = [[0.1] * 384]  # Only 1 vector for 2 chunks
        with patch("app.service.chunk_text_sentences") as chunk_mock:
            chunk_mock.return_value = ["chunk one", "chunk two"]
            with pytest.raises(EmbeddingError, match="mismatch"):
                from app.service import ingest_text
                ingest_text("x", doc_id="test")


@patch("app.service.query_vectors")
@patch("app.service.embed_single")
def test_search_handles_malformed_endee_response(embed_mock, query_mock):
    """Search tolerates malformed Endee response: similarity as str, id as int, meta None."""
    embed_mock.return_value = [0.1] * 384
    query_mock.return_value = [
        {"id": 12345, "similarity": "0.8", "meta": None},
        {"id": None, "similarity": None},
    ]
    results = search("test", top_k=5)
    assert len(results) == 2
    assert results[0]["id"] == "12345"
    assert results[0]["score"] == 0.8
    assert results[0]["text"] == ""
    assert results[1]["id"] == ""
    assert results[1]["score"] == 0.0
