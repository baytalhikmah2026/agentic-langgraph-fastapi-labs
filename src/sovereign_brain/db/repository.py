"""Read clients and users from the database. Endpoints use these instead of writing SQL."""

from typing import Annotated

from fastapi import Depends

from sovereign_brain.db.models import Client, User
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
