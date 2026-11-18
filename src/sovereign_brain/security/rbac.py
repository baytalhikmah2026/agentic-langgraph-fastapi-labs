"""Role-based access control (Lab 73): who may do what, written down in one place.

Three roles work at the Research Desk:
- analyst: asks for research and reports, reviews and approves other people's reports
- lead: everything an analyst does, plus overriding a waiting report (Lab 65)
- auditor: reads approvals and their history, but never changes anything
The API checks a permission before an endpoint runs; the approval graph checks again before
a report is released, so a forgotten check in one place is caught in the other.
"""

from collections.abc import Awaitable, Callable

from fastapi import HTTPException, status

from sovereign_brain.core.security import CurrentUser
from sovereign_brain.db.models import User

PERMISSIONS: dict[str, frozenset[str]] = {
    "research:run": frozenset({"analyst", "lead"}),
    "approvals:request": frozenset({"analyst", "lead"}),
    "approvals:decide": frozenset({"analyst", "lead"}),
    "approvals:override": frozenset({"lead"}),
    "approvals:read": frozenset({"analyst", "lead", "auditor"}),
}


def allowed(role: str, permission: str) -> bool:
    """True if the role has the permission; unknown roles and permissions get nothing."""
    return role in PERMISSIONS.get(permission, frozenset())


def require(permission: str) -> Callable[..., Awaitable[User]]:
    """A FastAPI dependency: the signed-in user must have this permission, or it is a 403."""

    async def check(user: CurrentUser) -> User:
        if not allowed(user.role, permission):
            detail = f"The role {user.role} may not use {permission}"
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail)
        return user

    return check
