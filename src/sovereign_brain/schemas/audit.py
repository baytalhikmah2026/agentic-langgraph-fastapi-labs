"""The audit log (Lab 77): what the audit endpoints return."""

from pydantic import BaseModel


class AuditEntry(BaseModel):
    seq: int
    at: str
    actor: str
    action: str
    subject: str
    details: dict
    hash: str


class AuditCheck(BaseModel):
    """The result of checking the whole chain, sealed with the desk's signature (Lab 76)."""

    events: int
    valid: bool
    problems: list[str]
    head_hash: str  # the newest entry's hash: it stands for the whole chain
    signature: str  # the desk's signature over events, valid and head_hash


class SecurityReport(BaseModel):
    """The desk's security posture at one moment, signed (Lab 80)."""

    posture: dict
    signature: str
