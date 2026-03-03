"""Domain models — pure dataclasses representing core business entities.

These models have ZERO dependencies on frameworks (no SQLAlchemy, no Pydantic).
They are the heart of the application — everything else depends on them,
but they depend on nothing external.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class LogEntry:
    """A single parsed log entry from an Nginx log file.

    Attributes:
        remote_addr: Client IP address.
        time_local: Timestamp of the request.
        method: HTTP method (GET, POST, etc.).
        path: Request path (e.g., /api/users).
        status: HTTP status code (200, 404, etc.).
        body_bytes_sent: Response body size in bytes.
        http_referer: Referer header value.
        http_user_agent: User-Agent header value.
        request_time: Request processing time in seconds (None if not in log format).
        source_file: Original log file name (for traceability).
        source_line: Line number in the original file.
        raw_line: Original raw log line (link to source).
    """

    remote_addr: str
    time_local: datetime
    method: str
    path: str
    status: int
    body_bytes_sent: int
    http_referer: str
    http_user_agent: str
    request_time: float | None
    source_file: str
    source_line: int
    raw_line: str


@dataclass(frozen=True)
class LogFile:
    """Metadata about an uploaded log file.

    Attributes:
        id: Unique identifier (assigned by DB).
        filename: Original uploaded file name.
        format_name: Log format used (e.g., "combined", "custom").
        total_lines: Total number of lines in the file.
        parsed_lines: Number of successfully parsed lines.
        error_lines: Number of lines that failed to parse.
        uploaded_at: When the file was uploaded.
        file_hash: SHA-256 hash for deduplication.
    """

    id: int | None
    filename: str
    format_name: str
    total_lines: int
    parsed_lines: int
    error_lines: int
    uploaded_at: datetime
    file_hash: str


@dataclass(frozen=True)
class UrlStat:
    """Per-URL aggregated statistics.

    Attributes:
        url: Request path.
        count: Absolute number of requests to this URL.
        count_perc: Percentage of total requests.
        time_sum: Total request_time for this URL (seconds).
        time_perc: Percentage of total request_time.
        time_avg: Average request_time (seconds).
        time_max: Maximum request_time (seconds).
        time_med: Median request_time (seconds).
    """

    url: str
    count: int
    count_perc: float
    time_sum: float
    time_perc: float
    time_avg: float
    time_max: float
    time_med: float


@dataclass(frozen=True)
class Statistics:
    """Aggregated statistics for a set of log entries.

    Attributes:
        total_requests: Total number of requests.
        avg_response_time: Average response time in ms (None if no timing data).
        median_response_time: Median (p50) response time in ms.
        p95_response_time: 95th percentile response time in ms.
        p99_response_time: 99th percentile response time in ms.
        status_distribution: Mapping of status code → request count.
        top_endpoints: List of (path, count) sorted by count descending.
        url_stats: Per-URL statistics with timing metrics.
        requests_per_minute: Time series of requests per minute.
    """

    total_requests: int
    avg_response_time: float | None = None
    median_response_time: float | None = None
    p95_response_time: float | None = None
    p99_response_time: float | None = None
    status_distribution: dict[int, int] = field(default_factory=dict)
    top_endpoints: list[tuple[str, int]] = field(default_factory=list)
    url_stats: list[UrlStat] = field(default_factory=list)
    requests_per_minute: list[tuple[datetime, int]] = field(default_factory=list)


@dataclass(frozen=True)
class Anomaly:
    """A detected anomaly in log data.

    Attributes:
        metric: Name of the anomalous metric (e.g., "p99_response_time").
        description: Human-readable description.
        severity: "low", "medium", "high", "critical".
        value: Observed value.
        expected_range: Expected range as (min, max) tuple.
    """

    metric: str
    description: str
    severity: str
    value: float
    expected_range: tuple[float, float]
