"""Read clients and users from the database. Endpoints use these instead of writing SQL."""

import json
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from sovereign_brain.db.models import Approval, ApprovalSignature, AuditEvent, Client, User
from sovereign_brain.db.session import DbSession
from sovereign_brain.security.audit_chain import GENESIS, entry_hash


class ClientRepository:
    def __init__(self, session: DbSession) -> None:
        self.session = session

    async def get(self, client_id: str) -> Client | None:
        return await self.session.get(Client, client_id)


Clients = Annotated[ClientRepository, Depends(ClientRepository)]


class UserRepository:
    def __init__(self, session: DbSession) -> None:
        self.session = session

    async def get(self, username: str) -> User | None:
        return await self.session.get(User, username)


Users = Annotated[UserRepository, Depends(UserRepository)]


class ApprovalRepository:
    """The approvals register (Lab 63): who asked for each report, and who decided."""

    def __init__(self, session: DbSession) -> None:
        self.session = session

    async def add(self, approval_id: str, client_id: str, requested_by: str) -> None:
        self.session.add(
            Approval(
                id=approval_id,
                client_id=client_id,
                requested_by=requested_by,
                requested_at=datetime.now(UTC),
                status="waiting",
            )
        )
        await self.session.commit()

    async def get(self, approval_id: str) -> Approval | None:
        return await self.session.get(Approval, approval_id)

    async def waiting(self) -> list[Approval]:
        """Every report still waiting for a decision, oldest first."""
        query = (
            select(Approval).where(Approval.status == "waiting").order_by(Approval.requested_at)
        )
        return list(await self.session.scalars(query))

    async def decide(
        self, approval: Approval, outcome: str, decided_by: str, comment: str | None
    ) -> None:
        approval.status = outcome
        approval.decided_by = decided_by
        approval.decided_at = datetime.now(UTC)
        approval.comment = comment
        await self.session.commit()

    async def add_signature(self, approval_id: str, statement: dict, signature: str) -> None:
        """Keep the signed statement of a decision (Lab 76)."""
        self.session.add(
            ApprovalSignature(
                approval_id=approval_id,
                statement=json.dumps(statement),
                signature=signature,
                signed_at=datetime.now(UTC),
            )
        )
        await self.session.commit()

    async def get_signature(self, approval_id: str) -> ApprovalSignature | None:
        return await self.session.get(ApprovalSignature, approval_id)


Approvals = Annotated[ApprovalRepository, Depends(ApprovalRepository)]


class AuditRepository:
    """The hash-chained audit log (Lab 77): append an entry, read them all in order."""

    def __init__(self, session: DbSession) -> None:
        self.session = session

    async def append(self, actor: str, action: str, subject: str, details: dict) -> AuditEvent:
        """Add one entry linked to the newest one; retried if another entry won the race."""
        for _ in range(3):
            last = await self.session.scalar(
                select(AuditEvent).order_by(AuditEvent.seq.desc()).limit(1)
            )
            prev_hash = last.hash if last else GENESIS
            at = datetime.now(UTC).isoformat(timespec="microseconds")
            text = json.dumps(details, sort_keys=True)
            event = AuditEvent(
                at=at,
                actor=actor,
                action=action,
                subject=subject,
                details=text,
                prev_hash=prev_hash,
                hash=entry_hash(prev_hash, at, actor, action, subject, text),
            )
            self.session.add(event)
            try:
                await self.session.commit()
                return event
            except IntegrityError:  # someone else linked to the same entry first
                await self.session.rollback()
        raise RuntimeError("The audit log is busy; please try again")

    async def events(self, limit: int | None = None) -> list[AuditEvent]:
        """All entries, oldest first (or only the newest `limit`, still oldest first)."""
        query = select(AuditEvent).order_by(AuditEvent.seq.desc())
        if limit is not None:
            query = query.limit(limit)
        return list(reversed(list(await self.session.scalars(query))))


AuditLog = Annotated[AuditRepository, Depends(AuditRepository)]
