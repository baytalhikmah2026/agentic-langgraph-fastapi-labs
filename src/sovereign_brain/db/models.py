"""Database tables of the Research Desk."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
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


class Position(Base):
    """One holding in a client's portfolio (Lab 22). Values in whole US dollars."""

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    ticker: Mapped[str] = mapped_column(String(12))
    name: Mapped[str] = mapped_column(String(80))
    sector: Mapped[str] = mapped_column(String(40))
    market_value_usd: Mapped[int]


class ResearchThread(Base):
    """One conversation thread and when it was last used (Lab 34): the basis for expiry."""

    __tablename__ = "research_threads"

    key: Mapped[str] = mapped_column(String(110), primary_key=True)  # "<username>:<thread_id>"
    owner: Mapped[str] = mapped_column(String(40))
    thread_id: Mapped[str] = mapped_column(String(64))
    client_id: Mapped[str] = mapped_column(String(6))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ThreadCleanup(Base):
    """One run of the thread clean-up (Lab 34): the evidence for the retention report."""

    __tablename__ = "thread_cleanups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ran_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    threads_removed: Mapped[int] = mapped_column(Integer)
    trigger: Mapped[str] = mapped_column(String(20))  # "worker" or "manual"


class Approval(Base):
    """The approvals register (Lab 63): one report waiting for a person, and the decision."""

    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # the approval_id
    client_id: Mapped[str] = mapped_column(String(6))
    requested_by: Mapped[str] = mapped_column(String(40))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(20))  # "waiting", "approved" or "rejected"
    decided_by: Mapped[str | None] = mapped_column(String(40))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    comment: Mapped[str | None] = mapped_column(String(500))


class ApprovalSignature(Base):
    """The signed statement about one decision (Lab 76), kept next to the register row."""

    __tablename__ = "approval_signatures"

    approval_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    statement: Mapped[str] = mapped_column(Text)  # the signed JSON, exactly as signed
    signature: Mapped[str] = mapped_column(String(120))  # base64 of the Ed25519 signature
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
