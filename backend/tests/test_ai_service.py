"""Tests for AIAnalyzerService — graceful degradation.

No actual LLM calls! We test the fallback behavior
when agent is None (AI not configured).
"""

import pytest

from log_analyzer.domain.models import Statistics
from log_analyzer.services.ai_analyzer import AIAnalyzerService


@pytest.fixture
def empty_stats() -> Statistics:
    """Empty statistics for testing."""
    return Statistics(
        total_requests=0,
        avg_response_time=None,
        median_response_time=None,
        p95_response_time=None,
        p99_response_time=None,
        status_distribution={},
        top_endpoints=[],
    )


class TestAIAnalyzerServiceNoAgent:
    """Tests when AI is not configured (agent=None)."""

    def test_available_false_when_no_agent(self) -> None:
        """Service reports unavailable when no agent."""
        service = AIAnalyzerService(agent=None)
        assert service.available is False

    @pytest.mark.skip(reason="Requires real AI agent with API key")
    def test_available_true_placeholder(self) -> None:
        """Service reports available when agent is provided."""

    @pytest.mark.asyncio
    async def test_summary_fallback(self, empty_stats: Statistics) -> None:
        """Summary returns warning message when no agent."""
        service = AIAnalyzerService(agent=None)
        result = await service.get_summary(empty_stats, [])

        assert "⚠️" in result
        assert "AI" in result

    @pytest.mark.asyncio
    async def test_chat_fallback(self, empty_stats: Statistics) -> None:
        """Chat yields warning message when no agent."""
        service = AIAnalyzerService(agent=None)
        chunks: list[str] = []

        async for chunk in service.get_chat_response("test?", empty_stats, []):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert "⚠️" in chunks[0]
