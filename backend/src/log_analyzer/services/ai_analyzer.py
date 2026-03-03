"""AI Analyzer service — orchestrates AI-powered log analysis.

Service layer: wraps AI provider through injected callables.
Handles graceful degradation when AI is not configured.
"""

from collections.abc import AsyncIterator, Callable
from typing import Any

import structlog

from log_analyzer.domain.models import LogEntry, Statistics

log = structlog.get_logger()

# Type aliases for AI callable signatures injected from infrastructure layer.
# `Any` is used for the agent parameter because its concrete type (pydantic_ai.Agent)
# belongs to the infrastructure layer and must not be imported in services.
SummarizeFn = Callable[..., Any]
ChatStreamFn = Callable[..., AsyncIterator[str]]


class AIAnalyzerService:
    """High-level AI analysis service.

    Wraps the low-level AI provider with:
    - Availability checking
    - Error handling with fallback messages
    - Structured logging
    """

    def __init__(
        self,
        agent: object | None,
        summarize_fn: SummarizeFn | None = None,
        chat_stream_fn: ChatStreamFn | None = None,
    ) -> None:
        """Initialize with optional AI agent and provider functions.

        Args:
            agent: AI agent instance, or None if AI is not configured.
            summarize_fn: Function to generate summaries.
            chat_stream_fn: Function to stream chat responses.
        """
        self._agent = agent
        self._summarize_fn = summarize_fn
        self._chat_stream_fn = chat_stream_fn

    @property
    def available(self) -> bool:
        """Check if AI analysis is available."""
        return self._agent is not None

    async def get_summary(
        self,
        statistics: Statistics,
        sample_entries: list[LogEntry],
    ) -> str:
        """Generate AI summary with anomaly detection.

        Returns fallback message if AI is not configured.
        """
        if self._agent is None or self._summarize_fn is None:
            return (
                "⚠️ AI-анализ недоступен. Настройте `OPENAI_API_KEY` или "
                "`DEEPSEEK_API_KEY` в переменных окружения."
            )

        try:
            result = await self._summarize_fn(self._agent, statistics, sample_entries)
            return str(result)
        except Exception:
            log.exception("ai_summary_failed")
            return "❌ Ошибка при генерации AI-анализа. Попробуйте позже."

    async def get_chat_response(
        self,
        question: str,
        statistics: Statistics,
        sample_entries: list[LogEntry],
    ) -> AsyncIterator[str]:
        """Stream AI chat response.

        Yields fallback message if AI is not configured.
        """
        if self._agent is None or self._chat_stream_fn is None:
            yield (
                "⚠️ AI-чат недоступен. Настройте `OPENAI_API_KEY` или "
                "`DEEPSEEK_API_KEY` в переменных окружения."
            )
            return

        try:
            async for chunk in self._chat_stream_fn(
                self._agent, question, statistics, sample_entries
            ):
                yield chunk
        except Exception:
            log.exception("ai_chat_failed", question=question[:100])
            yield "❌ Ошибка при генерации ответа. Попробуйте позже."
