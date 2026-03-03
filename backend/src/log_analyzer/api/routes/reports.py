"""Reports routes — list and retrieve uploaded log files.

GET /api/reports       — list all uploaded files
GET /api/reports/{id}  — get details of a specific file
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from log_analyzer.api.deps import get_repository
from log_analyzer.domain.interfaces import LogRepository

router = APIRouter(prefix="/api/reports", tags=["reports"])


class LogFileResponse(BaseModel):
    """Response model for log file metadata."""

    id: int
    filename: str
    format_name: str
    total_lines: int
    parsed_lines: int
    error_lines: int
    uploaded_at: str
    file_hash: str


class LogFileListResponse(BaseModel):
    """Response model for list of log files."""

    files: list[LogFileResponse]
    total: int


@router.get("", response_model=LogFileListResponse)
async def list_log_files(
    repository: Annotated[LogRepository, Depends(get_repository)],
) -> LogFileListResponse:
    """List all uploaded log files, newest first."""
    files = await repository.list_files()
    return LogFileListResponse(
        files=[
            LogFileResponse(
                id=f.id if f.id is not None else 0,
                filename=f.filename,
                format_name=f.format_name,
                total_lines=f.total_lines,
                parsed_lines=f.parsed_lines,
                error_lines=f.error_lines,
                uploaded_at=f.uploaded_at.isoformat(),
                file_hash=f.file_hash,
            )
            for f in files
        ],
        total=len(files),
    )


@router.get("/{file_id}", response_model=LogFileResponse)
async def get_log_file(
    file_id: int,
    repository: Annotated[LogRepository, Depends(get_repository)],
) -> LogFileResponse:
    """Get details of a specific uploaded log file."""
    log_file = await repository.get_file(file_id)
    if log_file is None:
        raise HTTPException(status_code=404, detail="Log file not found")

    return LogFileResponse(
        id=log_file.id if log_file.id is not None else 0,
        filename=log_file.filename,
        format_name=log_file.format_name,
        total_lines=log_file.total_lines,
        parsed_lines=log_file.parsed_lines,
        error_lines=log_file.error_lines,
        uploaded_at=log_file.uploaded_at.isoformat(),
        file_hash=log_file.file_hash,
    )


@router.delete("/{file_id}", status_code=204)
async def delete_log_file(
    file_id: int,
    repository: Annotated[LogRepository, Depends(get_repository)],
) -> None:
    """Delete a log file and all its entries.

    Returns 204 No Content on success, 404 if not found.
    """
    deleted = await repository.delete_file(file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Log file not found")
