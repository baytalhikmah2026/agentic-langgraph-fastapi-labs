"""Database tables of the Research Desk."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from sovereign_brain.db.base import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(6), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    segment: Mapped[str] = mapped_column(String(40))
    risk_profile: Mapped[str] = mapped_column(String(20))


class User(Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(40), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    hashed_password: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default="analyst")
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)
