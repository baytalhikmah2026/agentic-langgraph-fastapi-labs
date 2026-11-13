"""Request IDs: one label per request, in every log line, error answer and response header."""

import logging
import re
import uuid
from contextvars import ContextVar

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

HEADER = "X-Request-ID"
SAFE_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return request_id_var.get()


class RequestIdMiddleware:
    """Keeps a safe incoming X-Request-ID, or creates a new one, for every HTTP request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = dict(scope["headers"]).get(b"x-request-id", b"").decode("latin-1")
        request_id = incoming if SAFE_ID.match(incoming) else uuid.uuid4().hex
        # Each request runs in its own task, so this value is never seen by another request
        request_id_var.set(request_id)

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message).append(HEADER, request_id)
            await send(message)

        await self.app(scope, receive, send_with_id)


class RequestIdFilter(logging.Filter):
    """Adds the current request ID to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True
