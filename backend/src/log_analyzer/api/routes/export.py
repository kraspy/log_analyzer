"""Export routes — download log data in CSV format.

GET /api/export/{file_id}/csv — stream log entries as CSV.
"""

import csv
import io
from collections.abc import AsyncIterator
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from log_analyzer.api.deps import get_repository
from log_analyzer.domain.interfaces import LogRepository

log = structlog.get_logger()

router = APIRouter(prefix="/api/export", tags=["export"])

# How many entries to fetch per DB round-trip
_EXPORT_BATCH_SIZE = 5000


@router.get("/{file_id}/csv")
async def export_csv(
    file_id: int,
    repository: Annotated[LogRepository, Depends(get_repository)],
) -> StreamingResponse:
    """Export log entries as CSV.

    Uses StreamingResponse to avoid loading all entries into memory.
    Fetches entries in batches from the DB and writes CSV rows
    incrementally.

    Args:
        file_id: ID of the log file to export.
        repository: DB repository.

    Returns:
        CSV file download response.
    """
    # Verify file exists
    log_file = await repository.get_file(file_id)
    if log_file is None:
        raise HTTPException(status_code=404, detail="Log file not found")

    filename = log_file.filename.rsplit(".", 1)[0] + ".csv"

    async def generate_csv() -> AsyncIterator[str]:
        """Stream CSV rows in batches."""
        # Header row
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "timestamp",
                "ip",
                "method",
                "path",
                "status",
                "bytes",
                "response_time_ms",
                "referer",
                "user_agent",
            ]
        )
        yield output.getvalue()

        # Data rows in batches
        offset = 0
        while True:
            entries = await repository.get_entries(
                file_id,
                limit=_EXPORT_BATCH_SIZE,
                offset=offset,
            )
            if not entries:
                break

            output = io.StringIO()
            writer = csv.writer(output)
            for e in entries:
                writer.writerow(
                    [
                        e.time_local.isoformat(),
                        e.remote_addr,
                        e.method,
                        e.path,
                        e.status,
                        e.body_bytes_sent,
                        round(e.request_time * 1000, 2) if e.request_time else "",
                        e.http_referer,
                        e.http_user_agent,
                    ]
                )
            yield output.getvalue()

            offset += _EXPORT_BATCH_SIZE
            if len(entries) < _EXPORT_BATCH_SIZE:
                break

    log.info("csv_export", file_id=file_id, filename=filename)

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
