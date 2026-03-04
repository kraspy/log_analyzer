"""Unified URL statistics calculator.

Single source of truth for per-URL metric computation.
Used by both CLI (in-memory dict) and Web (data loaded from DB).

This is a pure function module with zero side effects — no I/O,
no database, no framework dependencies.  Both CLI and Web feed
it the same ``dict[url → list[request_time]]`` shape, so results
are guaranteed to match.
"""

import statistics as pystats

from log_analyzer.domain.models import UrlStat


def compute_url_stats(
    url_times: dict[str, list[float]],
    total_requests: int,
    report_size: int = 1000,
) -> list[UrlStat]:
    """Compute per-URL metrics from a URL → request_times mapping.

    Args:
        url_times: Mapping of URL path → list of request_time values.
                   ``None`` values must be filtered out **before** calling
                   this function (only real timing data should be included).
        total_requests: Total number of parsed requests (for ``count_perc``).
        report_size: Max number of URLs to include in the result.

    Returns:
        List of ``UrlStat`` sorted by ``time_sum`` descending,
        limited to *report_size* entries.
    """
    total_time = sum(sum(times) for times in url_times.values())

    result: list[UrlStat] = []
    for url, times in url_times.items():
        if not times:
            continue

        time_sum = sum(times)
        count = len(times)

        result.append(
            UrlStat(
                url=url,
                count=count,
                count_perc=round(count / total_requests * 100, 3) if total_requests else 0.0,
                time_sum=round(time_sum, 3),
                time_perc=round(time_sum / total_time * 100, 3) if total_time else 0.0,
                time_avg=round(time_sum / count, 3),
                time_max=round(max(times), 3),
                time_med=round(pystats.median(times), 3),
            )
        )

    result.sort(key=lambda s: s.time_sum, reverse=True)
    return result[:report_size]
