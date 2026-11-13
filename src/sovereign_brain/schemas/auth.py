"""Sign-in answers."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str
    full_name: str
    role: str
