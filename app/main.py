"""Application startup: FastAPI app, logging, routes."""

import logging
import sys

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api import router
from app.config import settings
from app.middleware import RequestIdFilter, RequestIdMiddleware

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | [%(request_id)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
for h in logging.root.handlers:
    h.addFilter(RequestIdFilter())
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Knowledge Base API",
    description="Vector search over documents using Endee",
    version="1.0.0",
)
app.add_middleware(RequestIdMiddleware)
app.include_router(router, prefix="/api/v1", tags=["api"])


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request, exc):
    """Return clear 422 for invalid input (empty, wrong format)."""
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "message": "Validation failed"},
    )


@app.get("/")
def root():
    """Root redirect to docs."""
    return {"message": "Knowledge Base API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
