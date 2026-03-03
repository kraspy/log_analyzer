"""Statistics routes — aggregated metrics for log files.

GET /api/stats/{log_file_id}  — compute and return statistics
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from log_analyzer.api.deps import get_repository, get_statistics_service
from log_analyzer.domain.interfaces import LogRepository
from log_analyzer.services.statistics import StatisticsService

router = APIRouter(prefix="/api/stats", tags=["statistics"])


class UrlStatResponse(BaseModel):
    """Per-URL statistics response model."""

    url: str
    count: int
    count_perc: float
    time_sum: float
    time_perc: float
    time_avg: float
    time_max: float
    time_med: float


class StatsResponse(BaseModel):
    """Response model for log file statistics."""

    total_requests: int
    avg_response_time: float | None
    median_response_time: float | None
    p95_response_time: float | None
    p99_response_time: float | None
    status_distribution: dict[int, int]
    top_endpoints: list[dict[str, int | str]]
    url_stats: list[UrlStatResponse]


@router.get("/{log_file_id}", response_model=StatsResponse)
async def get_statistics(
    log_file_id: int,
    repository: Annotated[LogRepository, Depends(get_repository)],
    stats_service: Annotated[StatisticsService, Depends(get_statistics_service)],
) -> StatsResponse:
    """Compute and return aggregated statistics for a log file.

    Calculates: total requests, response time percentiles,
    status code distribution, top endpoints, and per-URL stats.
    """
    # Verify file exists
    log_file = await repository.get_file(log_file_id)
    if log_file is None:
        raise HTTPException(status_code=404, detail="Log file not found")

    stats = await stats_service.calculate(log_file_id)

    return StatsResponse(
        total_requests=stats.total_requests,
        avg_response_time=stats.avg_response_time,
        median_response_time=stats.median_response_time,
        p95_response_time=stats.p95_response_time,
        p99_response_time=stats.p99_response_time,
        status_distribution=stats.status_distribution,
        top_endpoints=[{"path": path, "count": count} for path, count in stats.top_endpoints],
        url_stats=[
            UrlStatResponse(
                url=u.url,
                count=u.count,
                count_perc=u.count_perc,
                time_sum=u.time_sum,
                time_perc=u.time_perc,
                time_avg=u.time_avg,
                time_max=u.time_max,
                time_med=u.time_med,
            )
            for u in stats.url_stats
        ],
    )
