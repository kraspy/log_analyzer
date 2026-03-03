"""Preview route — POST /api/logs/preview.

Accepts raw log lines and tests them against a parser,
returning per-line parsing results so the frontend can
show which lines parse OK before a full upload.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from log_analyzer.api.deps import get_parser_service
from log_analyzer.domain.enums import LogFormat
from log_analyzer.services.parser import ParserService

router = APIRouter(prefix="/api/logs", tags=["logs"])


class PreviewRequest(BaseModel):
    """Request body for preview endpoint."""

    lines: list[str]
    format_name: LogFormat = LogFormat.COMBINED


class LineResult(BaseModel):
    """Parsing result for a single line."""

    line_number: int
    parsed: bool
    fields: dict[str, str | int | float | None] | None = None


class PreviewResponse(BaseModel):
    """Response with per-line parsing results."""

    results: list[LineResult]


@router.post("/preview", response_model=PreviewResponse)
async def preview_lines(
    body: PreviewRequest,
    parser_service: Annotated[ParserService, Depends(get_parser_service)],
) -> PreviewResponse:
    """Test-parse raw log lines without uploading.

    Used by the frontend to show a preview of whether each
    line parses successfully with the selected format.
    """
    parser = parser_service.get_parser(body.format_name)
    if parser is None:
        return PreviewResponse(results=[])

    results: list[LineResult] = []
    for i, line in enumerate(body.lines[:10], start=1):  # Max 10 lines
        entry = parser.parse_line(line.strip(), "preview", i)
        if entry is not None:
            results.append(
                LineResult(
                    line_number=i,
                    parsed=True,
                    fields={
                        "ip": entry.remote_addr,
                        "timestamp": entry.time_local.isoformat(),
                        "method": entry.method,
                        "path": entry.path,
                        "status": entry.status,
                        "bytes": entry.body_bytes_sent,
                        "response_time": entry.request_time,
                    },
                )
            )
        else:
            results.append(LineResult(line_number=i, parsed=False))

    return PreviewResponse(results=results)
