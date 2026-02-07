"""Integration tests that require a real Endee instance. Skipped if Endee is unavailable.

Run with: pytest tests/test_integration.py -v
Requires: Docker + Endee running on ENDEE_BASE_URL (default localhost:8080).
"""

import os
import socket
from unittest.mock import patch

import pytest

# Check if Endee is reachable before importing app (avoids loading heavy deps if skipping)
def _endee_available() -> bool:
    base = os.getenv("ENDEE_BASE_URL", "http://localhost:8080/api/v1")
    if "localhost" in base or "127.0.0.1" in base:
        try:
            host = "127.0.0.1" if "127.0.0.1" in base else "localhost"
            with socket.create_connection((host, 8080), timeout=2):
                return True
        except (OSError, socket.timeout):
            return False
    return True  # Assume available for remote URLs


requires_endee = pytest.mark.integration(
    pytest.mark.skipif(
        not _endee_available(),
        reason="Endee not reachable. Start with: docker run -d -p 8080:8080 -v endee-data:/data endeeio/endee-server:latest",
    )
)


@requires_endee
@patch("app.service.embed_texts")
@patch("app.service.embed_single")
def test_integration_ingest_and_search_real_endee(embed_texts_mock, embed_single_mock):
    """End-to-end: ingest via real Endee, then search. Embeddings mocked to avoid slow model load."""
    from app.service import ingest_text, search

    # Reset mocks (patch may already be applied)
    fake_vec = [0.1] * 384
    embed_texts_mock.return_value = [fake_vec]
    embed_single_mock.return_value = fake_vec

    text = "Integration test: Python is used for data science and web development."
    result = ingest_text(text, doc_id="integration-test-doc")
    assert result["doc_id"] == "integration-test-doc"
    assert result["chunks_stored"] >= 1

    results = search("What is Python used for?", top_k=3)
    assert len(results) >= 1
    assert any("data science" in r["text"] or "web" in r["text"] for r in results)
