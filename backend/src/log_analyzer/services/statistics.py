"""Statistics service — computes aggregated metrics from log data.

Uses the repository's analytics queries instead of loading raw data.
All heavy computation (GROUP BY, percentiles) happens in SQL or
uses pre-sorted data from the repository.
"""

import math
import statistics as pystats

import structlog

from log_analyzer.domain.interfaces import LogRepository
from log_analyzer.domain.models import Statistics, UrlStat

log = structlog.get_logger()


class StatisticsService:
    """Calculates statistics for a log file."""

    def __init__(self, repository: LogRepository) -> None:
        self._repo = repository

    async def calculate(self, log_file_id: int) -> Statistics:
        """Calculate aggregated statistics for a log file.

        Uses SQL aggregations where possible (status distribution,
        top endpoints). Percentiles use sorted response times from DB.

        Args:
            log_file_id: ID of the log file to analyze.

        Returns:
            Statistics dataclass with computed metrics.
        """
        # Get total request count
        total = await self._repo.get_entry_count(log_file_id)

        # Status code distribution (SQL GROUP BY)
        status_dist = await self._repo.get_status_distribution(log_file_id)

        # Top endpoints by request count
        top_endpoints = await self._repo.get_top_endpoints(log_file_id, limit=20)

        # Response time percentiles (from pre-sorted data)
        response_times = await self._repo.get_response_times(log_file_id)
        avg_rt, med_rt, p95_rt, p99_rt = _calculate_percentiles(response_times)

        # Per-URL statistics
        url_stats = await self._compute_url_stats(log_file_id, total)

        log.info(
            "statistics_calculated",
            log_file_id=log_file_id,
            total_requests=total,
            response_times_count=len(response_times),
            url_stats_count=len(url_stats),
        )

        return Statistics(
            total_requests=total,
            avg_response_time=avg_rt,
            median_response_time=med_rt,
            p95_response_time=p95_rt,
            p99_response_time=p99_rt,
            status_distribution=status_dist,
            top_endpoints=top_endpoints,
            url_stats=url_stats,
        )

    async def _compute_url_stats(self, log_file_id: int, total_requests: int) -> list[UrlStat]:
        """Compute per-URL statistics with medians and percentages."""
        raw_stats = await self._repo.get_url_stats(log_file_id)
        if not raw_stats:
            return []

        # Total time across all URLs (for time_perc)
        total_time: float = sum(
            float(s["time_sum"])
            for s in raw_stats  # type: ignore[arg-type, misc]
        )

        # Get response times per path for median calculation
        paths = [str(s["path"]) for s in raw_stats]
        rt_by_path = await self._repo.get_response_times_by_path(
            log_file_id,
            paths,
        )

        result: list[UrlStat] = []
        for s in raw_stats:
            path = str(s["path"])
            count = int(s["count"])  # type: ignore[call-overload]
            time_sum = float(s["time_sum"])  # type: ignore[arg-type]
            time_avg = float(s["time_avg"])  # type: ignore[arg-type]
            time_max = float(s["time_max"])  # type: ignore[arg-type]

            # Median from sorted response times
            path_times = rt_by_path.get(path, [])
            time_med = pystats.median(path_times) if path_times else 0.0

            # Percentages
            count_perc = round(count / total_requests * 100, 3) if total_requests else 0.0
            time_perc = round(time_sum / total_time * 100, 3) if total_time else 0.0

            result.append(
                UrlStat(
                    url=path,
                    count=count,
                    count_perc=count_perc,
                    time_sum=round(time_sum, 3),
                    time_perc=time_perc,
                    time_avg=round(time_avg, 3),
                    time_max=round(time_max, 3),
                    time_med=round(time_med, 3),
                )
            )

        return result


def _calculate_percentiles(
    sorted_values: list[float],
) -> tuple[float | None, float | None, float | None, float | None]:
    """Calculate avg, median, p95, p99 from pre-sorted values.

    Args:
        sorted_values: Response times sorted ascending.

    Returns:
        Tuple of (avg, median, p95, p99). All None if list is empty.
    """
    if not sorted_values:
        return None, None, None, None

    n = len(sorted_values)
    avg = sum(sorted_values) / n

    # Percentile function: get value at given percentile
    def pct(p: float) -> float:
        """Return the value at the given percentile ``p``."""
        idx = math.ceil(n * p / 100) - 1
        return sorted_values[max(0, min(idx, n - 1))]

    return (
        round(avg * 1000, 2),  # Convert to ms
        round(pct(50) * 1000, 2),  # Median
        round(pct(95) * 1000, 2),  # p95
        round(pct(99) * 1000, 2),  # p99
    )
