"""What the API shows about a client."""

from pydantic import BaseModel, ConfigDict


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    segment: str
    risk_profile: str
