"""Parser service — orchestrates log file parsing.

This is a Service layer component: it uses LogParser (interface)
to parse lines and coordinates the overall parsing workflow.
The service doesn't know HOW parsing works — it delegates to
the parser implementation injected via constructor (DI).
"""

import hashlib
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import structlog

from log_analyzer.domain.enums import LogFormat
from log_analyzer.domain.interfaces import LogParser
from log_analyzer.domain.models import LogEntry, LogFile

log = structlog.get_logger()


class ParserService:
    """Orchestrates parsing of log files.

    Attributes:
        _parsers: Mapping of format name → parser implementation.
    """

    def __init__(self, parsers: dict[LogFormat, LogParser]) -> None:
        """Initialize with available parsers.

        Args:
            parsers: Dict mapping LogFormat to concrete parser.
                     Injected via DI — service doesn't create parsers.
        """
        self._parsers = parsers

    def get_parser(self, format_name: LogFormat) -> LogParser | None:
        """Get parser by format name. Returns None if not registered."""
        return self._parsers.get(format_name)

    def parse_file(
        self,
        file_path: Path,
        format_name: LogFormat = LogFormat.COMBINED,
    ) -> tuple[LogFile, Iterator[LogEntry]]:
        """Parse a log file and return metadata + entry iterator.

        Uses an iterator (generator) instead of loading all entries
        into memory — this allows parsing multi-gigabyte files without
        running out of RAM.

        Args:
            file_path: Path to the log file.
            format_name: Which parser to use.

        Returns:
            Tuple of (LogFile metadata, iterator of parsed entries).

        Raises:
            ValueError: If no parser is registered for the format.
            FileNotFoundError: If file doesn't exist.
        """
        parser = self._parsers.get(format_name)
        if parser is None:
            msg = f"No parser registered for format: {format_name}"
            raise ValueError(msg)

        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)

        # Calculate file hash for deduplication
        file_hash = _calculate_file_hash(file_path)

        # Count lines for metadata
        total_lines = _count_lines(file_path)

        log.info(
            "parsing_file",
            file=file_path.name,
            format=format_name,
            total_lines=total_lines,
        )

        # Create metadata (parsed/error counts will be updated after parsing)
        log_file = LogFile(
            id=None,
            filename=file_path.name,
            format_name=format_name,
            total_lines=total_lines,
            parsed_lines=0,  # Updated after parsing
            error_lines=0,  # Updated after parsing
            uploaded_at=datetime.now(tz=UTC),
            file_hash=file_hash,
        )

        # Return iterator — lazy parsing, one line at a time
        entries = _parse_lines(parser, file_path)

        return log_file, entries


def _parse_lines(parser: LogParser, file_path: Path) -> Iterator[LogEntry]:
    """Generator: yields parsed entries one by one.

    This is a generator function — it reads one line at a time
    and yields parsed LogEntry objects. Memory usage is O(1)
    regardless of file size.
    """
    with file_path.open(encoding="utf-8", errors="replace") as f:
        for line_number, line in enumerate(f, start=1):
            entry = parser.parse_line(line, file_path.name, line_number)
            if entry is not None:
                yield entry


def _calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA-256 hash of a file for deduplication.

    Reads in 8KB chunks to handle large files without loading
    everything into memory.
    """
    hasher = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def _count_lines(file_path: Path) -> int:
    """Count lines in a file efficiently."""
    count = 0
    with file_path.open("rb") as f:
        for _ in f:
            count += 1
    return count
