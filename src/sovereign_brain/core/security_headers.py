"""Security headers (Lab 80): small, standard instructions on every answer the API sends.

They tell browsers and proxies how to treat our answers: never guess a content type, never
show the API inside another site's frame, never send our address on to other sites, and
never store answers from /v1/ (they can hold client data).
"""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

ALWAYS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"cross-origin-resource-policy", b"same-origin"),
]
API_ONLY = [(b"cache-control", b"no-store")]  # /v1/ answers: never kept by a cache


class SecurityHeadersMiddleware:
    """Adds the headers to every HTTP answer, whatever the endpoint returned."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        extra = ALWAYS + (API_ONLY if scope["path"].startswith("/v1/") else [])

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = [*message.get("headers", []), *extra]
            await send(message)

        await self.app(scope, receive, send_with_headers)
