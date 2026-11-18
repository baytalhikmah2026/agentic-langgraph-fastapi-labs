"""The security report (Lab 80): every layer of Module 8 in one signed answer."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from sovereign_brain.api.v1.approvals import DeskSigner
from sovereign_brain.core.security import get_current_user
from sovereign_brain.core.settings import get_settings
from sovereign_brain.db.repository import AuditLog
from sovereign_brain.schemas.audit import SecurityReport
from sovereign_brain.security.audit_chain import GENESIS, verify_chain
from sovereign_brain.security.injection import RULES
from sovereign_brain.security.rbac import PERMISSIONS, require

router = APIRouter(
    prefix="/v1/security",
    tags=["security"],
    dependencies=[Depends(get_current_user), Depends(require("audit:read"))],
)


@router.get("/report")
async def report(audit: AuditLog, signer: DeskSigner) -> SecurityReport:
    """What protects the desk right now, from the live settings and the audit chain."""
    settings = get_settings()
    chain = await audit.events()
    problems = verify_chain(chain)
    posture = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "injection_guard_rules": sorted(RULES),  # Lab 71
        "pii_masking": settings.pii_masking,  # Lab 72
        "permissions": {name: sorted(roles) for name, roles in PERMISSIONS.items()},  # Lab 73
        "market_mutual_tls": bool(settings.market_ca_file),  # Lab 74
        "secrets_from_vault": bool(settings.vault_addr),  # Lab 75
        "signing_key_id": signer.key_id,  # Lab 76
        "audit_chain": {  # Lab 77
            "events": len(chain),
            "valid": not problems,
            "head_hash": chain[-1].hash if chain else GENESIS,
        },
        "tracing": settings.otel_enabled,  # Lab 66
    }
    return SecurityReport(posture=posture, signature=signer.sign(posture))
