"""Research requests: the main counter of the Research Desk."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, status

from sovereign_brain.schemas.research import ResearchRequest, ResearchResponse

router = APIRouter(prefix="/v1/research", tags=["research"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def submit_research(request: ResearchRequest) -> ResearchResponse:
    return ResearchResponse(
        request_id=uuid4().hex,
        client_id=request.client_id,
        status="accepted",
        created_at=datetime.now(UTC),
    )
