"""Tests for the combined log parser."""

from log_analyzer.infrastructure.parsers.combined import CombinedLogParser


class TestCombinedLogParser:
    """Tests for CombinedLogParser."""

    def setup_method(self) -> None:
        """Create parser instance for each test."""
        self.parser = CombinedLogParser()

    def test_parse_standard_line(self) -> None:
        """Parse a standard combined-format log line."""
        line = (
            "93.180.71.3 - - [17/May/2015:08:05:32 +0000] "
            '"GET /downloads/product_1 HTTP/1.1" 304 0 "-" '
            '"Debian APT-HTTP/1.3 (0.8.16~exp12ubuntu10.21)"'
        )
        entry = self.parser.parse_line(line, "access.log", 1)

        assert entry is not None
        assert entry.remote_addr == "93.180.71.3"
        assert entry.method == "GET"
        assert entry.path == "/downloads/product_1"
        assert entry.status == 304
        assert entry.body_bytes_sent == 0
        assert entry.http_referer == "-"
        assert entry.http_user_agent == "Debian APT-HTTP/1.3 (0.8.16~exp12ubuntu10.21)"
        assert entry.source_file == "access.log"
        assert entry.source_line == 1
        assert entry.request_time is None

    def test_parse_line_with_request_time(self) -> None:
        """Parse a line that includes request_time at the end."""
        line = (
            "10.0.0.1 - admin [01/Jan/2026:12:00:00 +0000] "
            '"POST /api/users HTTP/2.0" 201 128 '
            '"https://example.com" "Mozilla/5.0" 0.045'
        )
        entry = self.parser.parse_line(line, "access.log", 42)

        assert entry is not None
        assert entry.method == "POST"
        assert entry.path == "/api/users"
        assert entry.status == 201
        assert entry.body_bytes_sent == 128
        assert entry.request_time == 0.045
        assert entry.source_line == 42

    def test_parse_empty_line_returns_none(self) -> None:
        """Empty lines should return None (skip gracefully)."""
        assert self.parser.parse_line("", "test.log", 1) is None
        assert self.parser.parse_line("   ", "test.log", 2) is None

    def test_parse_invalid_line_returns_none(self) -> None:
        """Lines that don't match combined format return None."""
        assert self.parser.parse_line("not a log line", "test.log", 1) is None
        assert self.parser.parse_line("random garbage 123", "test.log", 2) is None

    def test_parse_preserves_raw_line(self) -> None:
        """Raw line should be stored for traceability."""
        line = '1.2.3.4 - - [01/Jan/2026:00:00:00 +0000] "GET / HTTP/1.1" 200 1234 "-" "curl/7.0"'
        entry = self.parser.parse_line(line, "access.log", 5)

        assert entry is not None
        assert entry.raw_line == line

    def test_parse_various_http_methods(self) -> None:
        """Parser should handle all HTTP methods."""
        for method in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
            line = (
                f"1.2.3.4 - - [01/Jan/2026:00:00:00 +0000] "
                f'"{method} /test HTTP/1.1" 200 0 "-" "test"'
            )
            entry = self.parser.parse_line(line, "test.log", 1)
            assert entry is not None
            assert entry.method == method

    def test_parse_with_query_string(self) -> None:
        """Paths with query strings should be preserved."""
        line = (
            "1.2.3.4 - - [01/Jan/2026:00:00:00 +0000] "
            '"GET /search?q=hello&page=2 HTTP/1.1" 200 512 "-" "test"'
        )
        entry = self.parser.parse_line(line, "test.log", 1)

        assert entry is not None
        assert entry.path == "/search?q=hello&page=2"
