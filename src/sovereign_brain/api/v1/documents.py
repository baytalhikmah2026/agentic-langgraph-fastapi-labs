"""Long-document analysis (Lab 57): one request, many readers at the same time."""

import logging
from datetime import UTC, datetime
from pathlib import Path as FilePath
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from langgraph.graph.state import CompiledStateGraph

from sovereign_brain.core.rate_limit import model_call_gate
from sovereign_brain.core.request_id import get_request_id
from sovereign_brain.core.security import get_current_user
from sovereign_brain.core.settings import get_settings
from sovereign_brain.schemas.documents import DocumentAnalysis, DocumentRequest
from sovereign_brain.services.documents import DocumentNotFound, list_documents, load_document

router = APIRouter(
    prefix="/v1/documents", tags=["documents"], dependencies=[Depends(get_current_user)]
)
logger = logging.getLogger("sovereign_brain.documents")
DocumentName = Annotated[str, Path(pattern=r"^[a-z0-9-]+\.md$")]


def get_mapreduce_graph(request: Request) -> CompiledStateGraph:
    """The map-reduce graph built once at start-up (Lab 57)."""
    return request.app.state.mapreduce_graph


MapReduceGraph = Annotated[CompiledStateGraph, Depends(get_mapreduce_graph)]


@router.get("")
async def documents() -> list[str]:
    """The documents that can be analysed."""
    return list_documents(FilePath(get_settings().documents_dir))


@router.post("/{name}/analyse", dependencies=[Depends(model_call_gate)])
async def analyse(
    name: DocumentName, body: DocumentRequest, graph: MapReduceGraph
) -> DocumentAnalysis:
    """Split, read every piece at the same time, collapse if needed, and summarise."""
    settings = get_settings()
    try:
        text = load_document(FilePath(settings.documents_dir), name)
    except DocumentNotFound:
        raise HTTPException(status_code=404, detail=f"Document {name} not found") from None
    if not text.strip():
        raise HTTPException(status_code=422, detail=f"Document {name} is empty")
    config = {
        "max_concurrency": settings.map_max_concurrency,  # readers working at the same time
        "recursion_limit": settings.graph_recursion_limit,
        "metadata": {"request_id": get_request_id()},
    }
    result = await graph.ainvoke({"name": name, "text": text, "focus": body.focus}, config=config)
    logger.info("Analysed %s: %d pieces in %d round(s)", name, result["chunks"], result["rounds"])
    return DocumentAnalysis(
        request_id=get_request_id(),
        name=name,
        summary=result["summary"],
        chunks=result["chunks"],
        rounds=result["rounds"],
        created_at=datetime.now(UTC),
    )
