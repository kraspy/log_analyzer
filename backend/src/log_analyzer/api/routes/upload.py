"""Upload route — POST /api/logs/upload.

Handles multipart file upload, parsing, and storage.
Supports .gz compressed files (auto-detected by extension).
"""

import dataclasses
import gzip
import shutil
import tempfile
from pathlib import Path
from typing import Annotated

import anyio
import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel

from log_analyzer.api.deps import get_parser_service, get_repository, get_settings
from log_analyzer.config import Settings
from log_analyzer.domain.enums import LogFormat
from log_analyzer.domain.interfaces import LogRepository
from log_analyzer.domain.models import LogEntry
from log_analyzer.services.parser import ParserService

log = structlog.get_logger()

router = APIRouter(prefix="/api/logs", tags=["logs"])

# Batch size for bulk insert (trade-off: memory vs DB round-trips)
_BATCH_SIZE = 5000


class UploadResponse(BaseModel):
    """Response after successful file upload."""

    log_file_id: int
    filename: str
    total_lines: int
    parsed_lines: int
    error_lines: int
    message: str


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_log_file(
    file: UploadFile,
    settings: Annotated[Settings, Depends(get_settings)],
    parser_service: Annotated[ParserService, Depends(get_parser_service)],
    repository: Annotated[LogRepository, Depends(get_repository)],
    format_name: LogFormat = LogFormat.COMBINED,
) -> UploadResponse:
    """Upload and parse a log file.

    Supports `.gz` files — auto-decompressed before parsing.

    Workflow:
    1. Save uploaded file to disk
    2. If .gz → decompress to temp file
    3. Check for duplicates via SHA-256 hash
    4. Parse file line by line
    5. Batch insert entries into database
    6. Update file metadata with final counts
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    # 1. Save file to disk
    upload_dir = anyio.Path(settings.upload_dir)
    await upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = Path(settings.upload_dir) / file.filename

    with file_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    log.info("file_uploaded", filename=file.filename, path=str(file_path))

    # 2. Handle .gz files
    parse_path = file_path
    display_name = file.filename
    temp_file = None

    if file.filename.endswith(".gz"):
        display_name = file.filename[:-3]  # Strip .gz for display
        temp_file = tempfile.NamedTemporaryFile(  # noqa: SIM115
            suffix=".log",
            delete=False,
        )
        try:
            with gzip.open(file_path, "rb") as gz_in:
                shutil.copyfileobj(gz_in, temp_file)
            temp_file.close()
            parse_path = Path(temp_file.name)
            log.info(
                "gz_decompressed",
                original=file.filename,
                decompressed=parse_path.name,
            )
        except gzip.BadGzipFile as e:
            temp_file.close()
            await anyio.Path(temp_file.name).unlink(missing_ok=True)
            raise HTTPException(
                status_code=400,
                detail=f"Invalid gzip file: {e}",
            ) from e

    # 3. Parse file (get metadata + lazy entry iterator)
    try:
        log_file, entries = parser_service.parse_file(parse_path, format_name)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Use display name (without .gz) for storage
    log_file = dataclasses.replace(log_file, filename=display_name)

    # 3. Check for duplicate uploads
    if await repository.file_exists_by_hash(log_file.file_hash):
        raise HTTPException(
            status_code=409,
            detail=f"File already uploaded (hash: {log_file.file_hash[:12]}...)",
        )

    # 4. Save file metadata
    saved_file = await repository.save_file(log_file)
    assert saved_file.id is not None

    # 5. Batch insert entries
    parsed_count = 0
    batch: list[LogEntry] = []

    for entry in entries:
        batch.append(entry)
        if len(batch) >= _BATCH_SIZE:
            await repository.save_entries(batch, saved_file.id)
            parsed_count += len(batch)
            batch = []

    # Save remaining entries
    if batch:
        await repository.save_entries(batch, saved_file.id)
        parsed_count += len(batch)

    error_count = log_file.total_lines - parsed_count

    # Update file record with actual counts
    await repository.update_file_counts(saved_file.id, parsed_count, error_count)

    # Cleanup temp file if gzip was decompressed
    if temp_file is not None:
        await anyio.Path(temp_file.name).unlink(missing_ok=True)

    log.info(
        "file_parsed",
        file_id=saved_file.id,
        parsed=parsed_count,
        errors=error_count,
    )

    return UploadResponse(
        log_file_id=saved_file.id,
        filename=display_name,
        total_lines=log_file.total_lines,
        parsed_lines=parsed_count,
        error_lines=error_count,
        message=f"Successfully parsed {parsed_count}/{log_file.total_lines} lines",
    )
