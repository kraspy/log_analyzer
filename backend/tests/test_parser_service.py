"""Tests for ParserService — orchestration layer.

Tests the service that coordinates parsers, not the parsers themselves.
Parser unit tests are in test_parser.py.
"""

from pathlib import Path

import pytest

from log_analyzer.domain.enums import LogFormat
from log_analyzer.infrastructure.parsers.combined import CombinedLogParser
from log_analyzer.services.parser import ParserService


@pytest.fixture
def parser_service() -> ParserService:
    """Parser service with combined parser registered."""
    return ParserService(
        parsers={LogFormat.COMBINED: CombinedLogParser()},
    )


@pytest.fixture
def sample_log_file(tmp_path: Path) -> Path:
    """Create a temporary log file with 3 valid lines + 1 invalid."""
    content = (
        '10.0.0.1 - - [01/Jan/2026:00:00:01 +0000] "GET /a HTTP/1.1" 200 100 "-" "test" 0.01\n'
        "not a valid log line\n"
        '10.0.0.2 - - [01/Jan/2026:00:00:02 +0000] "POST /b HTTP/1.1" 201 200 "-" "test" 0.02\n'
        '10.0.0.3 - - [01/Jan/2026:00:00:03 +0000] "GET /c HTTP/1.1" 404 0 "-" "test"\n'
    )
    log_file = tmp_path / "test.log"
    log_file.write_text(content)
    return log_file


class TestParserService:
    """Tests for ParserService."""

    def test_parse_file_metadata(
        self,
        parser_service: ParserService,
        sample_log_file: Path,
    ) -> None:
        """parse_file returns correct metadata."""
        log_file, _entries = parser_service.parse_file(sample_log_file, "combined")

        assert log_file.filename == "test.log"
        assert log_file.format_name == "combined"
        assert log_file.total_lines == 4
        assert log_file.file_hash  # Should be non-empty SHA256

    def test_parse_file_entries(
        self,
        parser_service: ParserService,
        sample_log_file: Path,
    ) -> None:
        """parse_file yields only valid entries (skips invalid lines)."""
        _log_file, entries = parser_service.parse_file(sample_log_file, "combined")
        entry_list = list(entries)  # Consume the generator

        # 3 valid lines, 1 invalid → 3 entries
        assert len(entry_list) == 3
        assert entry_list[0].path == "/a"
        assert entry_list[1].path == "/b"
        assert entry_list[2].path == "/c"

    def test_parse_file_source_tracking(
        self,
        parser_service: ParserService,
        sample_log_file: Path,
    ) -> None:
        """Each entry tracks its source file and line number."""
        _log_file, entries = parser_service.parse_file(sample_log_file, "combined")
        entry_list = list(entries)

        assert entry_list[0].source_line == 1
        assert entry_list[1].source_line == 3  # Line 2 was invalid, so 3rd line
        assert entry_list[2].source_line == 4

    def test_parse_file_hash_is_deterministic(
        self,
        parser_service: ParserService,
        sample_log_file: Path,
    ) -> None:
        """Same file content → same hash (SHA-256 dedup)."""
        log_file1, _ = parser_service.parse_file(sample_log_file, "combined")
        # Consume generator to reset
        log_file2, _ = parser_service.parse_file(sample_log_file, "combined")

        assert log_file1.file_hash == log_file2.file_hash

    def test_unknown_format_raises(
        self,
        parser_service: ParserService,
        sample_log_file: Path,
    ) -> None:
        """Unknown format name raises ValueError."""
        with pytest.raises(ValueError, match="No parser registered"):
            parser_service.parse_file(sample_log_file, "unknown_format")

    def test_missing_file_raises(self, parser_service: ParserService) -> None:
        """Non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parser_service.parse_file(Path("/nonexistent/file.log"), "combined")
