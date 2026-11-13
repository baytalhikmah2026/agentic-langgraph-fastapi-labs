"""Sign-in: exchange a username and password for a signed access token."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from sovereign_brain.core.security import (
    CurrentUser,
    create_access_token,
    not_authenticated,
    verify_password,
)
from sovereign_brain.core.settings import get_settings
from sovereign_brain.db.repository import Users
from sovereign_brain.schemas.auth import Token, UserOut

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/token")
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], users: Users) -> Token:
    user = await users.get(form.username)
    if user is None or user.disabled or not verify_password(form.password, user.hashed_password):
        raise not_authenticated("Wrong username or password")
    token, expires_in = create_access_token(user, get_settings())
    return Token(access_token=token, expires_in=expires_in)


@router.get("/me")
async def who_am_i(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
