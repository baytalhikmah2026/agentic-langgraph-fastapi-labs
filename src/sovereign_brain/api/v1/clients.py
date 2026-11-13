"""Client look-up: the bank's client register."""

from fastapi import APIRouter, HTTPException, status

from sovereign_brain.db.repository import Clients
from sovereign_brain.schemas.client import ClientOut

router = APIRouter(prefix="/v1/clients", tags=["clients"])


@router.get("/{client_id}")
async def get_client(client_id: str, clients: Clients) -> ClientOut:
    client = await clients.get(client_id.upper())
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Client {client_id} not found")
    return ClientOut.model_validate(client)
