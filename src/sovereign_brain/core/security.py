"""Passwords, sign-in tokens and the current user."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash

from sovereign_brain.core.settings import Settings, get_settings
from sovereign_brain.db.models import User
from sovereign_brain.db.repository import Users

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_access_token(user: User, settings: Settings) -> tuple[str, int]:
    """A signed token that says who the user is and until when it is valid."""
    lifetime = timedelta(minutes=settings.access_token_minutes)
    claims = {"sub": user.username, "role": user.role, "exp": datetime.now(UTC) + lifetime}
    secret = settings.jwt_secret.get_secret_value()
    token = jwt.encode(claims, secret, algorithm=settings.jwt_algorithm)
    return token, int(lifetime.total_seconds())


def not_authenticated(message: str) -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED, message, headers={"WWW-Authenticate": "Bearer"}
    )


async def get_current_user(
    request: Request, token: Annotated[str, Depends(oauth2_scheme)], users: Users
) -> User:
    settings = get_settings()
    try:
        claims = jwt.decode(
            token, settings.jwt_secret.get_secret_value(), algorithms=[settings.jwt_algorithm]
        )
    except jwt.ExpiredSignatureError as error:
        raise not_authenticated("The sign-in token has expired") from error
    except jwt.InvalidTokenError as error:
        raise not_authenticated("The sign-in token is not valid") from error

    user = await users.get(claims.get("sub", ""))
    if user is None or user.disabled:
        raise not_authenticated("Unknown or disabled user")
    if claims.get("role") != user.role:  # Lab 73: a changed role needs a new sign-in
        raise not_authenticated("Your role has changed; please sign in again")
    request.state.username = user.username
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
