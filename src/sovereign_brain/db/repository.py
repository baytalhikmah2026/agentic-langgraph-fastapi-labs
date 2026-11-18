"""Read clients and users from the database. Endpoints use these instead of writing SQL."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select

from sovereign_brain.db.models import Approval, Client, User
from sovereign_brain.db.session import DbSession


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


Approvals = Annotated[ApprovalRepository, Depends(ApprovalRepository)]
