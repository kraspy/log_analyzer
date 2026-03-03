"""Parser for Nginx combined log format.

The combined format is the most common Nginx log format:
    $remote_addr - $remote_user [$time_local] "$request" $status
    $body_bytes_sent "$http_referer" "$http_user_agent"

Example line:
    93.180.71.3 - - [17/May/2015:08:05:32 +0000] "GET /downloads/product_1 HTTP/1.1"
    304 0 "-" "Debian APT-HTTP/1.3 (0.8.16~exp12ubuntu10.21)"

The parser uses a compiled regex for performance — parsing millions
of lines needs to be fast.
"""

import contextlib
import re
from datetime import datetime

import structlog

from log_analyzer.domain.interfaces import LogParser
from log_analyzer.domain.models import LogEntry

log = structlog.get_logger()

# Compiled regex for the combined log format.
# Each group captures one field from the log line.
_COMBINED_PATTERN = re.compile(
    r"(?P<remote_addr>\S+)"  # 93.180.71.3
    r"\s+\S+\s+"  # ident (usually "-" or hex id) + flexible whitespace
    r"(?P<remote_user>\S+)"  # - (or username)
    r"\s+\[(?P<time_local>[^\]]+)\]"  # [17/May/2015:08:05:32 +0000]
    r'\s+"(?P<request>[^"]*)"'  # "GET /downloads/product_1 HTTP/1.1"
    r"\s+(?P<status>\d{3})"  # 304
    r"\s+(?P<body_bytes_sent>\d+)"  # 0
    r'\s+"(?P<http_referer>[^"]*)"'  # "-"
    r'\s+"(?P<http_user_agent>[^"]*)"'  # "Debian APT-HTTP/1.3 ..."
    r"(?P<trailing>.*)"  # any trailing fields (request_time, ids, etc.)
)

# Nginx time format: 17/May/2015:08:05:32 +0000
_TIME_FORMAT = "%d/%b/%Y:%H:%M:%S %z"


class CombinedLogParser(LogParser):
    """Parser for Nginx combined log format.

    Thread-safe: uses compiled regex, no mutable state.
    """

    def parse_line(self, line: str, file_name: str, line_number: int) -> LogEntry | None:
        """Parse a single combined-format log line.

        Args:
            line: Raw log line string.
            file_name: Source file name for traceability.
            line_number: Line number in the source file.

        Returns:
            Parsed LogEntry, or None if line doesn't match the format.
        """
        stripped = line.strip()
        if not stripped:
            return None

        match = _COMBINED_PATTERN.match(stripped)
        if not match:
            log.debug("parse_line_failed", file=file_name, line=line_number)
            return None

        groups = match.groupdict()

        # Parse timestamp
        try:
            time_local = datetime.strptime(groups["time_local"], _TIME_FORMAT)
        except ValueError:
            log.debug("invalid_timestamp", file=file_name, line=line_number)
            return None

        # Parse request line: "GET /path HTTP/1.1" → method, path
        method, path = _parse_request(groups["request"])

        # Parse optional request_time from trailing fields
        # In extended formats, request_time is typically the last numeric token
        request_time: float | None = None
        trailing = groups.get("trailing", "").strip()
        if trailing:
            # Try last token as request_time (e.g. '... "id1" "id2" 0.390')
            last_token = trailing.rsplit(maxsplit=1)[-1] if trailing else ""
            with contextlib.suppress(ValueError):
                request_time = float(last_token)

        return LogEntry(
            remote_addr=groups["remote_addr"],
            time_local=time_local,
            method=method,
            path=path,
            status=int(groups["status"]),
            body_bytes_sent=int(groups["body_bytes_sent"]),
            http_referer=groups["http_referer"],
            http_user_agent=groups["http_user_agent"],
            request_time=request_time,
            source_file=file_name,
            source_line=line_number,
            raw_line=stripped,
        )


def _parse_request(request_str: str) -> tuple[str, str]:
    """Extract HTTP method and path from request string.

    Args:
        request_str: e.g. "GET /downloads/product_1 HTTP/1.1"

    Returns:
        Tuple of (method, path). Defaults to ("UNKNOWN", request_str)
        if parsing fails.
    """
    parts = request_str.split(" ", maxsplit=2)
    if len(parts) >= 2:
        return parts[0], parts[1]
    return "UNKNOWN", request_str
