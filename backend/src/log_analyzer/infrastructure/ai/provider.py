"""AI provider — pydantic_ai Agent wrapping OpenAI/DeepSeek.

pydantic_ai is a type-safe framework for working with LLMs.
It creates "agents" — configured LLM instances with:
- System prompt (who the AI is)
- Result type (structured output)
- Tools (functions the AI can call)

We use it here for two modes:
1. Summary — single-shot analysis returning structured text
2. Chat — streaming responses via SSE
"""

from collections.abc import AsyncIterator

import structlog
from pydantic_ai import Agent

from log_analyzer.domain.models import LogEntry, Statistics

log = structlog.get_logger()

# System prompt shared by both summary and chat modes
_SYSTEM_PROMPT = """You are an expert Nginx log analyst. You analyze HTTP access logs
and provide actionable insights about:
- Traffic patterns and anomalies
- Performance issues (slow endpoints, high response times)
- Error patterns (4xx, 5xx spikes)
- Security concerns (unusual IPs, suspicious paths)
- Capacity planning recommendations

Be concise, use bullet points, and highlight critical findings.
Respond in the same language as the user's question (default: Russian)."""


def _format_context(
    statistics: Statistics,
    sample_entries: list[LogEntry],
    max_samples: int = 50,
) -> str:
    """Format statistics and sample entries as context for the LLM.

    We send aggregated stats + a sample of raw entries —
    never the entire log file (would exceed context window).

    Args:
        statistics: Aggregated metrics.
        sample_entries: Representative log entries.
        max_samples: Max number of sample entries to include.

    Returns:
        Formatted context string.
    """
    lines = [
        "## Log Statistics",
        f"- Total requests: {statistics.total_requests}",
    ]

    if statistics.avg_response_time is not None:
        lines.append(f"- Avg response time: {statistics.avg_response_time:.1f}ms")
    if statistics.median_response_time is not None:
        lines.append(f"- Median response time: {statistics.median_response_time:.1f}ms")
    if statistics.p95_response_time is not None:
        lines.append(f"- P95 response time: {statistics.p95_response_time:.1f}ms")
    if statistics.p99_response_time is not None:
        lines.append(f"- P99 response time: {statistics.p99_response_time:.1f}ms")

    if statistics.status_distribution:
        lines.append("\n## Status Code Distribution")
        for code, count in sorted(statistics.status_distribution.items()):
            pct = count / statistics.total_requests * 100 if statistics.total_requests else 0
            lines.append(f"- {code}: {count} ({pct:.1f}%)")

    if statistics.top_endpoints:
        lines.append("\n## Top Endpoints")
        for path, count in statistics.top_endpoints[:10]:
            lines.append(f"- {path}: {count} requests")

    # Include sample log entries for detail
    samples = sample_entries[:max_samples]
    if samples:
        lines.append(f"\n## Sample Log Entries ({len(samples)} of {len(sample_entries)})")
        for entry in samples:
            rt = f" {entry.request_time:.3f}s" if entry.request_time else ""
            lines.append(
                f"- [{entry.time_local:%H:%M:%S}] {entry.method} {entry.path} → {entry.status}{rt}"
            )

    return "\n".join(lines)


def create_ai_agent(
    model_name: str = "openai:gpt-5.2-nano",
) -> Agent[None, str]:
    """Create a pydantic_ai Agent for log analysis.

    Args:
        model_name: LLM model identifier.
            OpenAI: "openai:gpt-5.2-nano", "openai:gpt-5.2-mini"
            DeepSeek: "deepseek:deepseek-chat"

    Returns:
        Configured Agent instance.
    """
    return Agent(
        model_name,
        system_prompt=_SYSTEM_PROMPT,
        output_type=str,
    )


async def summarize(
    agent: Agent[None, str],
    statistics: Statistics,
    sample_entries: list[LogEntry],
) -> str:
    """Generate a text summary with anomaly highlights.

    Single-shot call — sends context + prompt, gets back full response.

    Args:
        agent: Configured pydantic_ai Agent.
        statistics: Aggregated statistics for context.
        sample_entries: Representative log entries.

    Returns:
        Markdown-formatted summary text.
    """
    context = _format_context(statistics, sample_entries)
    prompt = f"""Analyze these Nginx logs and provide:
1. **Summary** — brief overview of traffic patterns
2. **Anomalies** — anything unusual or concerning
3. **Recommendations** — actionable next steps

{context}"""

    result = await agent.run(prompt)
    log.info("ai_summary_generated", model=str(agent.model))
    return result.output


async def chat_stream(
    agent: Agent[None, str],
    question: str,
    statistics: Statistics,
    sample_entries: list[LogEntry],
) -> AsyncIterator[str]:
    """Answer a question about logs, streaming response chunks.

    Uses pydantic_ai's streaming API — yields text chunks
    as they arrive from the LLM. Frontend receives these via SSE.

    Args:
        agent: Configured pydantic_ai Agent.
        question: User's natural language question.
        statistics: Aggregated stats for context.
        sample_entries: Representative entries.

    Yields:
        Response text chunks.
    """
    context = _format_context(statistics, sample_entries)
    prompt = f"""Based on these Nginx logs, answer the following question:

**Question:** {question}

{context}"""

    async with agent.run_stream(prompt) as stream:
        async for chunk in stream.stream_text(delta=True):
            yield chunk

    log.info("ai_chat_completed", question=question[:100])
