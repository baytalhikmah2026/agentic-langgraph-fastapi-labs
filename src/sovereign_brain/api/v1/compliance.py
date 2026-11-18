"""The regulator's desk (Lab 95): signed compliance reports, built from the desk's records."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from sovereign_brain.api.v1.approvals import DeskSigner
from sovereign_brain.api.v1.security import report as security_report
from sovereign_brain.compliance.report import build_report, to_markdown
from sovereign_brain.core.security import CurrentUser, get_current_user
from sovereign_brain.db.repository import AuditLog
from sovereign_brain.schemas.audit import ComplianceReport
from sovereign_brain.security.rbac import require

router = APIRouter(
    prefix="/v1/compliance",
    tags=["compliance"],
    dependencies=[Depends(get_current_user), Depends(require("compliance:read"))],
)
Days = Annotated[int, Query(ge=1, le=366)]


async def sealed_report(
    audit: AuditLog, signer: DeskSigner, user: CurrentUser, days: int
) -> ComplianceReport:
    posture = (await security_report(audit, signer)).posture  # the live settings (Lab 80)
    report = build_report(await audit.events(), posture, days)
    await audit.append(user.username, "compliance.report_issued", "desk", {"days": days})
    return ComplianceReport(report=report, signature=signer.sign(report), key_id=signer.key_id)


@router.get("/report")
async def compliance_report(
    audit: AuditLog, signer: DeskSigner, user: CurrentUser, days: Days = 30
) -> ComplianceReport:
    """Every control with its rule, status and evidence, signed with the desk's key."""
    return await sealed_report(audit, signer, user, days)


@router.get("/report.md", response_class=PlainTextResponse)
async def compliance_report_markdown(
    audit: AuditLog, signer: DeskSigner, user: CurrentUser, days: Days = 30
) -> str:
    """The same report as a Markdown page for people."""
    sealed = await sealed_report(audit, signer, user, days)
    return to_markdown(sealed.report, sealed.signature, sealed.key_id)
