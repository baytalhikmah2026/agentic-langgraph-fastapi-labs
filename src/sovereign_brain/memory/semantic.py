"""Semantic memory (Lab 38): what the Research Desk learned, stored by meaning in Qdrant.

A thread remembers one conversation (Labs 31-37). Semantic memory remembers across all of
them: every finished answer becomes a vector (a list of numbers that captures its meaning)
and is stored in Qdrant with its details. A new question becomes a vector too, and Qdrant
returns the stored answers whose vectors point in the most similar direction.
"""

import logging
from datetime import UTC, datetime
from uuid import uuid4

from langchain_core.embeddings import Embeddings
from pydantic import BaseModel, Field
from qdrant_client import AsyncQdrantClient, models

from sovereign_brain.graphs.routing import Route

logger = logging.getLogger("sovereign_brain.memory")

# nomic-embed-text was trained with these task prefixes: stored texts and questions differ
DOCUMENT_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "


class MemoryRecord(BaseModel):
    """One remembered answer: the payload stored next to its vector."""

    owner: str = Field(min_length=1)  # the analyst: memories are never shared between analysts
    client_id: str = Field(pattern=r"^C-\d{4}$")
    thread_id: str
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    route: Route
    saved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def text(self) -> str:
        """What the embedding model reads: the question and its answer together."""
        return f"Question: {self.question}\nAnswer: {self.answer}"


class Recollection(MemoryRecord):
    """A remembered answer found again, with its similarity to the new question (up to 1)."""

    score: float


class SemanticMemory:
    """Stores and finds remembered answers in one Qdrant collection."""

    def __init__(
        self,
        client: AsyncQdrantClient,
        embeddings: Embeddings,
        collection: str,
        dimensions: int,
        min_score: float = 0.6,
    ) -> None:
        self.client = client
        self.embeddings = embeddings
        self.collection = collection
        self.dimensions = dimensions
        self.min_score = min_score  # below this similarity, a memory does not count as related
        self.ready = False

    async def ensure_collection(self) -> None:
        """Create the collection the first time it is needed (cosine similarity)."""
        if self.ready:
            return
        if not await self.client.collection_exists(self.collection):
            await self.client.create_collection(
                self.collection,
                vectors_config=models.VectorParams(
                    size=self.dimensions, distance=models.Distance.COSINE
                ),
            )
            logger.info(
                "Created Qdrant collection %s (%d dimensions, cosine)",
                self.collection,
                self.dimensions,
            )
        self.ready = True

    async def remember(self, record: MemoryRecord) -> str:
        """Store one answer with its vector; returns the new point's ID."""
        await self.ensure_collection()
        [vector] = await self.embeddings.aembed_documents([DOCUMENT_PREFIX + record.text()])
        point_id = str(uuid4())
        await self.client.upsert(
            self.collection,
            points=[
                models.PointStruct(
                    id=point_id, vector=vector, payload=record.model_dump(mode="json")
                )
            ],
        )
        return point_id

    async def recall(
        self, owner: str, client_id: str, question: str, limit: int = 3
    ) -> list[Recollection]:
        """The stored answers closest in meaning to `question`, for one analyst and client."""
        await self.ensure_collection()
        vector = await self.embeddings.aembed_query(QUERY_PREFIX + question)
        response = await self.client.query_points(
            self.collection,
            query=vector,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(key="owner", match=models.MatchValue(value=owner)),
                    models.FieldCondition(
                        key="client_id", match=models.MatchValue(value=client_id)
                    ),
                ]
            ),
            limit=limit,
            score_threshold=self.min_score,
            with_payload=True,
        )
        return [Recollection(**point.payload, score=point.score) for point in response.points]

    async def forget_client(self, client_id: str) -> int:
        """Delete every memory about one client, for every analyst (Lab 78); returns how many."""
        await self.ensure_collection()
        about_client = models.Filter(
            must=[
                models.FieldCondition(key="client_id", match=models.MatchValue(value=client_id))
            ]
        )
        found = await self.client.count(self.collection, count_filter=about_client, exact=True)
        await self.client.delete(
            self.collection, points_selector=models.FilterSelector(filter=about_client)
        )
        return found.count
