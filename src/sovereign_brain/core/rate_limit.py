"""Rate limits for expensive model calls, counted per signed-in analyst."""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from sovereign_brain.core.security import CurrentUser
from sovereign_brain.core.settings import get_settings


def rate_limit_key(request: Request) -> str:
    """Count per analyst; fall back to the caller's address if nobody is signed in."""
    username = getattr(request.state, "username", None)
    return f"user:{username}" if username else f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=rate_limit_key, storage_uri=get_settings().rate_limit_storage_uri)


@limiter.limit(get_settings().model_rate_limit)
async def model_call_gate(request: Request, user: CurrentUser) -> None:
    """One shared gate for every endpoint that runs the model: each call counts once."""
