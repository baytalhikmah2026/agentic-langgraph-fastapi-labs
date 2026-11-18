"""Role-based access control (Lab 73): who may do what, written down in one place.

Three roles work at the Research Desk:
- analyst: asks for research and reports, reviews and approves other people's reports
- lead: everything an analyst does, plus overriding a waiting report (Lab 65)
- auditor: reads approvals and their history, but never changes anything
The API checks a permission before an endpoint runs; the approval graph checks again before
a report is released, so a forgotten check in one place is caught in the other.
"""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status

from sovereign_brain.core.security import CurrentUser, oauth2_scheme, token_scopes
from sovereign_brain.db.models import User

PERMISSIONS: dict[str, frozenset[str]] = {
    "research:run": frozenset({"analyst", "lead"}),
    "approvals:request": frozenset({"analyst", "lead"}),
    "approvals:decide": frozenset({"analyst", "lead"}),
    "approvals:override": frozenset({"lead"}),
    "approvals:read": frozenset({"analyst", "lead", "auditor"}),
    "audit:read": frozenset({"lead", "auditor"}),  # Lab 77
    "privacy:erase": frozenset({"lead"}),  # Lab 78
    "compliance:read": frozenset({"lead", "auditor", "regulator"}),  # Lab 95
    "brain:run": frozenset({"analyst", "lead"}),  # Lab 99: start a Brain run
    "brain:decide": frozenset({"analyst", "lead"}),  # Lab 99: approve or reject one
}


def allowed(role: str, permission: str) -> bool:
    """True if the role has the permission; unknown roles and permissions get nothing."""
    return role in PERMISSIONS.get(permission, frozenset())


def grant(role: str, requested: list[str]) -> list[str]:
    """The scopes a new token gets (Lab 99): what was asked for and the role allows.

    Asking for nothing means "everything my role allows"; scopes the role doesn't have
    are left out, as OAuth2 allows, so a sign-in can only ever narrow its own power.
    """
    mine = sorted(name for name, roles in PERMISSIONS.items() if role in roles)
    return [scope for scope in requested if scope in mine] if requested else mine


def require_scope(scope: str) -> Callable[..., Awaitable[User]]:
    """A FastAPI dependency: this sign-in's token must carry the scope, or it is a 403."""

    async def check(user: CurrentUser, token: Annotated[str, Depends(oauth2_scheme)]) -> User:
        if scope not in token_scopes(token):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"This sign-in lacks the scope {scope}")
        return user

    return check


def require(permission: str) -> Callable[..., Awaitable[User]]:
    """A FastAPI dependency: the signed-in user must have this permission, or it is a 403."""

    async def check(user: CurrentUser) -> User:
        if not allowed(user.role, permission):
            detail = f"The role {user.role} may not use {permission}"
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail)
        return user

    return check
