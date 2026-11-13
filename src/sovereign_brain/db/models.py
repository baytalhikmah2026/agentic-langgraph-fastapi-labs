"""Database tables of the Research Desk."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from sovereign_brain.db.base import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(6), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    segment: Mapped[str] = mapped_column(String(40))
    risk_profile: Mapped[str] = mapped_column(String(20))
