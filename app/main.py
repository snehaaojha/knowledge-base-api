"""Application startup: FastAPI app, logging, routes."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Preload embedding model at startup so health checks don't block."""
    import asyncio
    try:
        from app import embeddings
        await asyncio.to_thread(embeddings.get_embedding_model)
        logger.info("Embedding model preloaded")
    except Exception as e:
        logger.warning("Could not preload embedding model: %s", e)
    yield
    # shutdown: nothing to clean up


app = FastAPI(
    title="Knowledge Base API",
    description="Vector search over documents using Endee",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIdMiddleware)
app.include_router(router, prefix="/api/v1", tags=["api"])


def _json_safe(obj: object) -> object:
    """Recursively ensure obj is JSON-serializable."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, BaseException):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(x) for x in obj]
    return str(obj)


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request, exc):
    """Return clear 422 for invalid input (empty, wrong format)."""
    return JSONResponse(
        status_code=422,
        content={"detail": _json_safe(exc.errors()), "message": "Validation failed"},
    )


def _safe_detail(detail: object) -> str | list | dict | None:
    """Ensure detail is JSON-serializable."""
    if detail is None or isinstance(detail, (str, int, float, bool)):
        return detail
    if isinstance(detail, (list, dict)):
        return detail
    if hasattr(detail, "model_dump"):
        return detail.model_dump()
    return str(detail)


@app.exception_handler(Exception)
def generic_exception_handler(request, exc):
    """Return JSON 500 for uncaught exceptions instead of HTML."""
    if isinstance(exc, StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": _safe_detail(exc.detail)},
        )
    log = logging.getLogger(__name__)
    log.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/")
def root():
    """Root redirect to docs."""
    return {"message": "Knowledge Base API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
