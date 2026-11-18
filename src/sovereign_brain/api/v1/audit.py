"""The audit log (Lab 77): read the newest entries, and check the whole chain."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from sovereign_brain.api.v1.approvals import DeskSigner
from sovereign_brain.core.security import get_current_user
from sovereign_brain.db.repository import AuditLog
from sovereign_brain.schemas.audit import AuditCheck, AuditEntry
from sovereign_brain.security.audit_chain import GENESIS, verify_chain
from sovereign_brain.security.rbac import require

router = APIRouter(
    prefix="/v1/audit",
    tags=["audit"],
    dependencies=[Depends(get_current_user), Depends(require("audit:read"))],
)


@router.get("/events")
async def events(
    audit: AuditLog, limit: Annotated[int, Query(ge=1, le=500)] = 50
) -> list[AuditEntry]:
    """The newest entries of the audit log, oldest first."""
    return [
        AuditEntry(
            seq=event.seq,
            at=event.at,
            actor=event.actor,
            action=event.action,
            subject=event.subject,
            details=json.loads(event.details),
            hash=event.hash,
        )
        for event in await audit.events(limit)
    ]


@router.get("/verify")
async def verify(audit: AuditLog, signer: DeskSigner) -> AuditCheck:
    """Walk the whole chain; the result is signed, so it can be filed as evidence."""
    chain = await audit.events()
    problems = verify_chain(chain)
    head = chain[-1].hash if chain else GENESIS
    summary = {"events": len(chain), "valid": not problems, "head_hash": head}
    return AuditCheck(**summary, problems=problems, signature=signer.sign(summary))
