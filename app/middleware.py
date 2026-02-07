"""Request correlation: request_id for logging and response headers."""

import logging
import uuid
from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class RequestIdFilter(logging.Filter):
    """Add request_id to log records when present."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get() or "-"
        return True


class RequestIdMiddleware:
    """Inject request_id from header or generate; add to response and logs. Pure ASGI."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        headers = {}
        for k, v in scope.get("headers", []):
            try:
                key = k.decode("latin-1", errors="replace").lower()
                val = v.decode("latin-1", errors="replace")
                headers[key] = val
            except Exception:
                continue
        rid = headers.get("x-request-id") or str(uuid.uuid4())[:16]

        scope.setdefault("state", {})["request_id"] = rid
        token = request_id_ctx.set(rid)

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers_list = list(message.get("headers", []))
                headers_list.append((b"x-request-id", rid.encode("latin-1")))
                message = {**message, "headers": headers_list}
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            request_id_ctx.reset(token)
