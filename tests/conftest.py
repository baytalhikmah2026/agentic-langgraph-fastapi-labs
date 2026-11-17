"""Shared test fixtures: one place that builds the test application (Labs 17-40)."""

import asyncio
import itertools
from collections.abc import AsyncIterator, Callable, Iterable, Iterator, Sequence
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langgraph.checkpoint.memory import InMemorySaver
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from sovereign_brain.api.v1.research import (
    get_archivist,
    get_memory,
    get_portfolio,
    get_research_graph,
    get_thread_registry,
)
from sovereign_brain.core.cache import ResearchCache
from sovereign_brain.core.rate_limit import limiter
from sovereign_brain.core.security import hash_password
from sovereign_brain.db.base import Base
from sovereign_brain.db.models import Client, Position, User
from sovereign_brain.db.session import get_session
from sovereign_brain.graphs.research import build_research_graph
from sovereign_brain.main import create_app
from sovereign_brain.memory.retention import ThreadRegistry
from sovereign_brain.memory.semantic import SemanticMemory
from sovereign_brain.services.portfolio import PortfolioService

FAKE_ANSWER = "Energy stocks are a modest part of this client's portfolio."
PASSWORD = "correct-horse-battery-42"
PASSWORD_HASH = hash_password(PASSWORD)  # hashed once: Argon2 is slow on purpose


class FakeToolModel(GenericFakeChatModel):
    """The tests' fake model, able to take tools: it ignores them and gives scripted replies."""

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> "FakeToolModel":
        return self


class FailsOnce:
    """Scripted replies with one failure: call number `fail_on_call` finds the model down."""

    def __init__(self, replies: Iterable[BaseMessage], fail_on_call: int) -> None:
        self.replies = iter(replies)
        self.fail_on_call = fail_on_call
        self.calls = 0

    def __iter__(self) -> "FailsOnce":
        return self

    def __next__(self) -> BaseMessage:
        self.calls += 1
        if self.calls == self.fail_on_call:
            raise ConnectionError("The AI model is not reachable")
        return next(self.replies)


class WordEmbeddings(Embeddings):
    """A tiny stand-in for the embedding model (Lab 38): one number per finance word.

    Texts that share words point in similar directions, which is enough to test recall.
    The last number is always 1, so no text is ever an all-zero vector.
    """

    WORDS = ("bond", "energy", "financial", "share", "exposure", "risk")

    def vector(self, text: str) -> list[float]:
        words = text.lower().replace("?", " ").replace(".", " ").split()
        return [float(sum(w.startswith(word) for w in words)) for word in self.WORDS] + [1.0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.vector(text)


def seed_rows() -> list:
    return [
        Client(id="C-1042", name="Amina Rahman Holdings", segment="private-banking",
               risk_profile="moderate"),
        Client(id="C-2077", name="Northgate Logistics Ltd", segment="corporate",
               risk_profile="conservative"),
        User(username="amina", full_name="Amina Rahman", hashed_password=PASSWORD_HASH,
             role="analyst", disabled=False),
        User(username="former.analyst", full_name="Former Analyst",
             hashed_password=PASSWORD_HASH, role="analyst", disabled=True),
        User(username="omar", full_name="Omar Siddiqui", hashed_password=PASSWORD_HASH,
             role="analyst", disabled=False),
        Position(id=1, client_id="C-1042", ticker="GLFP", name="Gulf Petroleum Co",
                 sector="Energy", market_value_usd=120000),
        Position(id=2, client_id="C-1042", ticker="SNRS", name="Sunrise Solar",
                 sector="Energy", market_value_usd=65000),
        Position(id=3, client_id="C-1042", ticker="MDNB", name="Medina Bank",
                 sector="Financials", market_value_usd=815000),
    ]


@pytest.fixture
def make_model() -> Callable[[Iterable[BaseMessage]], FakeToolModel]:
    """Builds a fake model that gives the listed replies, one per call."""

    def make(replies: Iterable[BaseMessage]) -> FakeToolModel:
        return FakeToolModel(messages=iter(replies))

    return make


@pytest.fixture
def make_flaky_model() -> Callable[[Iterable[BaseMessage], int], FakeToolModel]:
    """Builds a fake model whose model server is down for exactly one call (Lab 35)."""

    def make(replies: Iterable[BaseMessage], fail_on_call: int = 1) -> FakeToolModel:
        return FakeToolModel(messages=FailsOnce(replies, fail_on_call))

    return make


@pytest.fixture
def make_memory() -> Callable[[], SemanticMemory]:
    """Builds a semantic memory in an in-process Qdrant (no server) with word embeddings."""

    def make() -> SemanticMemory:
        dimensions = len(WordEmbeddings.WORDS) + 1
        client = AsyncQdrantClient(location=":memory:")
        return SemanticMemory(client, WordEmbeddings(), "test_memory", dimensions, min_score=0.5)

    return make


@pytest.fixture
def fake_answer() -> str:
    """What the fake model answers in every test."""
    return FAKE_ANSWER


@pytest.fixture
def password() -> str:
    """The password of the test users."""
    return PASSWORD


@pytest.fixture(autouse=True)
def reset_rate_limits() -> None:
    """Every test starts with empty rate-limit counters."""
    limiter.reset()


@pytest.fixture(autouse=True)
def in_memory_cache(monkeypatch: pytest.MonkeyPatch) -> dict[str, dict]:
    """Tests never need Redis: the cache keeps its answers in a dictionary instead."""
    store: dict[str, dict] = {}

    async def get(self: ResearchCache, client_id: str, question: str) -> dict | None:
        return store.get(self.key(client_id, question))

    async def set(self: ResearchCache, client_id: str, question: str, result: dict) -> None:
        store[self.key(client_id, question)] = result

    monkeypatch.setattr(ResearchCache, "get", get)
    monkeypatch.setattr(ResearchCache, "set", set)
    return store


@pytest.fixture
def database_url(tmp_path: Path) -> str:
    """A fresh SQLite database file for each test, with two clients and two users."""
    url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"

    async def create_and_seed() -> None:
        engine = create_async_engine(url)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(engine)() as session:
            session.add_all(seed_rows())
            await session.commit()
        await engine.dispose()

    asyncio.run(create_and_seed())
    return url


@pytest.fixture
def app(database_url: str) -> FastAPI:
    """The real application, with the test database and a fake model that always answers."""
    application = create_app()
    engine = create_async_engine(database_url, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def test_session() -> AsyncIterator[AsyncSession]:
        async with sessions() as session:
            yield session

    model = FakeToolModel(messages=itertools.cycle([AIMessage(FAKE_ANSWER)]))
    graph = build_research_graph(model, checkpointer=InMemorySaver())
    portfolio = PortfolioService(sessions)
    application.dependency_overrides[get_session] = test_session
    application.dependency_overrides[get_research_graph] = lambda: graph
    application.dependency_overrides[get_portfolio] = lambda: portfolio
    registry = ThreadRegistry(sessions)
    application.dependency_overrides[get_thread_registry] = lambda: registry
    application.dependency_overrides[get_memory] = lambda: None  # memory off unless a test says so
    application.dependency_overrides[get_archivist] = lambda: None
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def sign_in(client: TestClient, username: str) -> dict[str, str]:
    """Signs in through the real token endpoint and returns the Authorization header."""
    response = client.post("/v1/auth/token", data={"username": username, "password": PASSWORD})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    """Signs in as amina."""
    return sign_in(client, "amina")


@pytest.fixture
def omar_headers(client: TestClient) -> dict[str, str]:
    """Signs in as omar, a second analyst (Lab 40)."""
    return sign_in(client, "omar")
