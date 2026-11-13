"""Read clients from the database. Endpoints use this instead of writing SQL themselves."""

from typing import Annotated

from fastapi import Depends

from sovereign_brain.db.models import Client
from sovereign_brain.db.session import DbSession


class ClientRepository:
    def __init__(self, session: DbSession) -> None:
        self.session = session

    async def get(self, client_id: str) -> Client | None:
        return await self.session.get(Client, client_id)


Clients = Annotated[ClientRepository, Depends(ClientRepository)]
