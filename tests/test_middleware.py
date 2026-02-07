"""Middleware tests: request_id propagation."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware import RequestIdMiddleware


@pytest.fixture
def app_with_middleware():
    """Minimal app with RequestIdMiddleware for isolation."""
    app = FastAPI()

    @app.get("/test")
    def test():
        return {"ok": True}

    app.add_middleware(RequestIdMiddleware)
    return app


def test_middleware_adds_request_id_when_missing(app_with_middleware):
    """Request gets X-Request-ID when not provided."""
    client = TestClient(app_with_middleware)
    resp = client.get("/test")
    assert resp.status_code == 200
    assert "X-Request-ID" in resp.headers
    assert len(resp.headers["X-Request-ID"]) > 0


def test_middleware_preserves_request_id_from_header(app_with_middleware):
    """Request ID from header is preserved in response."""
    client = TestClient(app_with_middleware)
    resp = client.get("/test", headers={"X-Request-ID": "my-custom-id-456"})
    assert resp.status_code == 200
    assert resp.headers["X-Request-ID"] == "my-custom-id-456"
