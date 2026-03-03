"""AI routes — summary and chat endpoints.

POST /api/ai/summary  — one-shot analysis
POST /api/ai/chat     — streaming chat via SSE
GET  /api/ai/status   — check AI availability
"""

from collections.abc import AsyncIterator
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from log_analyzer.api.deps import get_ai_service, get_repository, get_statistics_service
from log_analyzer.domain.interfaces import LogRepository
from log_analyzer.services.ai_analyzer import AIAnalyzerService
from log_analyzer.services.statistics import StatisticsService

log = structlog.get_logger()

router = APIRouter(prefix="/api/ai", tags=["ai"])

# Number of sample entries to send to AI (for context)
_SAMPLE_SIZE = 100


class SummaryRequest(BaseModel):
    """Request body for AI summary."""

    log_file_id: int


class SummaryResponse(BaseModel):
    """Response with AI-generated summary."""

    summary: str
    ai_available: bool


class ChatRequest(BaseModel):
    """Request body for AI chat."""

    log_file_id: int
    question: str


class AIStatusResponse(BaseModel):
    """AI service availability status."""

    available: bool
    message: str


@router.get("/status", response_model=AIStatusResponse)
async def ai_status(
    ai_service: Annotated[AIAnalyzerService, Depends(get_ai_service)],
) -> AIStatusResponse:
    """Check if AI analysis is available.

    Frontend uses this to show/hide AI features.
    """
    if ai_service.available:
        return AIStatusResponse(available=True, message="AI analysis is available")
    return AIStatusResponse(
        available=False,
        message="AI not configured. Set OPENAI_API_KEY or DEEPSEEK_API_KEY.",
    )


@router.post("/summary", response_model=SummaryResponse)
async def generate_summary(
    request: SummaryRequest,
    ai_service: Annotated[AIAnalyzerService, Depends(get_ai_service)],
    repository: Annotated[LogRepository, Depends(get_repository)],
    stats_service: Annotated[StatisticsService, Depends(get_statistics_service)],
) -> SummaryResponse:
    """Generate AI summary for a log file.

    Workflow:
    1. Verify file exists
    2. Calculate statistics
    3. Get sample entries
    4. Send to AI for analysis
    """
    # Verify file
    log_file = await repository.get_file(request.log_file_id)
    if log_file is None:
        raise HTTPException(status_code=404, detail="Log file not found")

    # Get statistics and samples
    statistics = await stats_service.calculate(request.log_file_id)
    samples = await repository.get_entries(request.log_file_id, limit=_SAMPLE_SIZE)

    # Generate summary
    summary = await ai_service.get_summary(statistics, samples)

    return SummaryResponse(summary=summary, ai_available=ai_service.available)


@router.post("/chat")
async def chat(
    request: ChatRequest,
    ai_service: Annotated[AIAnalyzerService, Depends(get_ai_service)],
    repository: Annotated[LogRepository, Depends(get_repository)],
    stats_service: Annotated[StatisticsService, Depends(get_statistics_service)],
) -> StreamingResponse:
    """Chat with AI about logs, streaming via SSE.

    SSE (Server-Sent Events) streams text chunks as they arrive
    from the LLM. Frontend reads them via EventSource API.

    SSE format: each chunk is sent as:
        data: chunk text here\\n\\n
    """
    # Verify file
    log_file = await repository.get_file(request.log_file_id)
    if log_file is None:
        raise HTTPException(status_code=404, detail="Log file not found")

    # Get context
    statistics = await stats_service.calculate(request.log_file_id)
    samples = await repository.get_entries(request.log_file_id, limit=_SAMPLE_SIZE)

    async def event_generator() -> AsyncIterator[str]:
        """Generate SSE events from AI response chunks."""
        async for chunk in ai_service.get_chat_response(request.question, statistics, samples):
            # SSE format: "data: ...\n\n"
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
