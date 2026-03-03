"""FastAPI Dependency Injection — wiring services to request handlers.

DI is the mechanism that connects all Clean Architecture layers:
  API handlers → Services → Repository → Database Session

Each `Depends(get_xxx)` in a route handler gets a properly
configured instance for that request. Session is created per-request
and committed/rolled back automatically.
"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from log_analyzer.config import Settings
from log_analyzer.domain.enums import LogFormat
from log_analyzer.domain.interfaces import LogRepository
from log_analyzer.infrastructure.ai.provider import chat_stream, create_ai_agent, summarize
from log_analyzer.infrastructure.db.repository import SQLAlchemyLogRepository
from log_analyzer.infrastructure.parsers.combined import CombinedLogParser
from log_analyzer.services.ai_analyzer import AIAnalyzerService
from log_analyzer.services.parser import ParserService
from log_analyzer.services.statistics import StatisticsService


def get_settings(request: Request) -> Settings:
    """Get application settings from app state."""
    return request.app.state.settings  # type: ignore[no-any-return]


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    """Get session factory from app state."""
    return request.app.state.session_factory  # type: ignore[no-any-return]


async def get_session(
    factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
) -> AsyncIterator[AsyncSession]:
    """Yield a database session per request.

    Commits on success, rolls back on exception.
    """
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LogRepository:
    """Get log repository for the current request."""
    return SQLAlchemyLogRepository(session)


async def get_parser_service() -> ParserService:
    """Get parser service with registered parsers."""
    return ParserService(
        parsers={LogFormat.COMBINED: CombinedLogParser()},
    )


async def get_statistics_service(
    repo: Annotated[LogRepository, Depends(get_repository)],
) -> StatisticsService:
    """Get statistics service for the current request."""
    return StatisticsService(repository=repo)


async def get_ai_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AIAnalyzerService:
    """Get AI analyzer service.

    If no AI API key is configured, returns a service with agent=None.
    All AI methods will return graceful fallback responses.
    """
    agent = None
    if settings.openai_api_key:
        agent = create_ai_agent("openai:gpt-5.2-nano")
    elif settings.deepseek_api_key:
        agent = create_ai_agent("deepseek:deepseek-chat")

    return AIAnalyzerService(
        agent=agent,
        summarize_fn=summarize,
        chat_stream_fn=chat_stream,
    )
