"""Privacy (Lab 78): the retention policy, and erasure of one client's working data."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path

from sovereign_brain.api.v1.research import Memory, Registry, ResearchGraph
from sovereign_brain.core.cache import Cache
from sovereign_brain.core.security import CurrentUser, get_current_user
from sovereign_brain.core.settings import get_settings
from sovereign_brain.db.repository import AuditLog
from sovereign_brain.memory.erasure import erase_client, retention_policy
from sovereign_brain.security.rbac import require

router = APIRouter(
    prefix="/v1/privacy", tags=["privacy"], dependencies=[Depends(get_current_user)]
)
ClientId = Annotated[str, Path(pattern=r"^C-\d{4}$")]


@router.get("/policy")
async def policy() -> list[dict[str, str]]:
    """What the desk keeps, for how long, and what an erasure does to it."""
    return retention_policy(get_settings())


@router.post("/erasure/{client_id}", dependencies=[Depends(require("privacy:erase"))])
async def erasure(
    client_id: ClientId,
    user: CurrentUser,
    registry: Registry,
    graph: ResearchGraph,
    memory: Memory,
    cache: Cache,
    audit: AuditLog,
) -> dict[str, int]:
    """Erase one client's conversations, memories and cached answers (GDPR Art. 17)."""
    removed = await erase_client(client_id, registry, graph, memory, cache)
    await audit.append(user.username, "privacy.erased", client_id, removed)
    return removed
