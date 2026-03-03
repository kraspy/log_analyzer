"""Domain interfaces — abstract contracts for infrastructure implementations.

These ABCs define WHAT the application needs, not HOW it's done.
Infrastructure layer provides concrete implementations (PostgreSQL, OpenAI, etc.).
Services depend on these interfaces via Dependency Injection.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from log_analyzer.domain.models import Anomaly, LogEntry, LogFile, Statistics


class LogParser(ABC):
    """Contract for parsing Nginx log lines."""

    @abstractmethod
    def parse_line(self, line: str, file_name: str, line_number: int) -> LogEntry | None:
        """Parse a single log line.

        Args:
            line: Raw log line string.
            file_name: Name of the source file (for traceability).
            line_number: Line number in the source file.

        Returns:
            Parsed LogEntry, or None if the line is invalid.
        """


class LogRepository(ABC):
    """Contract for log data persistence and analytics."""

    # ── CRUD ──────────────────────────────────────

    @abstractmethod
    async def save_file(self, log_file: LogFile) -> LogFile:
        """Save log file metadata. Returns file with assigned ID."""

    @abstractmethod
    async def save_entries(self, entries: list[LogEntry], log_file_id: int) -> int:
        """Save log entries in batch. Returns count of saved entries."""

    @abstractmethod
    async def get_file(self, file_id: int) -> LogFile | None:
        """Get log file metadata by ID."""

    @abstractmethod
    async def list_files(self) -> list[LogFile]:
        """List all uploaded log files."""

    @abstractmethod
    async def get_entries(
        self,
        log_file_id: int,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[LogEntry]:
        """Retrieve log entries for a file with pagination."""

    @abstractmethod
    async def file_exists_by_hash(self, file_hash: str) -> bool:
        """Check if a file with this hash has already been uploaded."""

    @abstractmethod
    async def update_file_counts(self, file_id: int, parsed_lines: int, error_lines: int) -> None:
        """Update parsed/error line counts after parsing is complete."""

    @abstractmethod
    async def delete_file(self, file_id: int) -> bool:
        """Delete a log file and all its entries. Returns True if deleted."""

    # ── Analytics ──────────────────────────────────

    @abstractmethod
    async def get_entry_count(self, log_file_id: int) -> int:
        """Get total entry count for a file."""

    @abstractmethod
    async def get_status_distribution(self, log_file_id: int) -> dict[int, int]:
        """Get status code distribution for a file."""

    @abstractmethod
    async def get_top_endpoints(self, log_file_id: int, limit: int = 10) -> list[tuple[str, int]]:
        """Get most requested endpoints."""

    @abstractmethod
    async def get_response_times(self, log_file_id: int) -> list[float]:
        """Get all non-null response times for statistical calculations."""

    @abstractmethod
    async def get_url_stats(self, log_file_id: int, limit: int = 1000) -> list[dict[str, object]]:
        """Get per-URL aggregated statistics."""

    @abstractmethod
    async def get_response_times_by_path(
        self, log_file_id: int, paths: list[str]
    ) -> dict[str, list[float]]:
        """Get response times grouped by path for median calculation."""


class StatisticsCalculator(ABC):
    """Contract for computing statistics from log entries."""

    @abstractmethod
    async def calculate(self, log_file_id: int) -> Statistics:
        """Calculate aggregated statistics for a log file."""

    @abstractmethod
    async def detect_anomalies(self, statistics: Statistics) -> list[Anomaly]:
        """Detect anomalies in the given statistics."""


class AIAnalyzer(ABC):
    """Contract for AI-powered log analysis."""

    @abstractmethod
    async def summarize(
        self,
        statistics: Statistics,
        sample_entries: list[LogEntry],
    ) -> str:
        """Generate a text summary with anomaly highlights.

        Args:
            statistics: Aggregated statistics for context.
            sample_entries: Representative log entries for detail.

        Returns:
            Markdown-formatted summary text.
        """

    @abstractmethod
    async def chat(
        self,
        question: str,
        statistics: Statistics,
        sample_entries: list[LogEntry],
    ) -> AsyncIterator[str]:
        """Answer a question about logs, streaming response chunks.

        Args:
            question: User's natural language question.
            statistics: Aggregated statistics for context.
            sample_entries: Representative log entries for detail.

        Yields:
            Response text chunks for SSE streaming.
        """
