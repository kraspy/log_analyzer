"""Repository implementation — concrete LogRepository using SQLAlchemy.

This is where Domain interfaces meet Infrastructure.
The repository converts between Domain dataclasses and ORM models,
hiding all SQLAlchemy details from the Service layer.
"""

from datetime import UTC

import structlog
from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from log_analyzer.domain.interfaces import LogRepository
from log_analyzer.domain.models import LogEntry, LogFile
from log_analyzer.infrastructure.db.models import LogEntryORM, LogFileORM

log = structlog.get_logger()


class SQLAlchemyLogRepository(LogRepository):
    """LogRepository implementation using async SQLAlchemy.

    Converts between Domain models (dataclasses) and ORM models
    at the repository boundary.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_file(self, log_file: LogFile) -> LogFile:
        """Save log file metadata and return with assigned ID."""
        orm = LogFileORM(
            filename=log_file.filename,
            format_name=log_file.format_name,
            total_lines=log_file.total_lines,
            parsed_lines=log_file.parsed_lines,
            error_lines=log_file.error_lines,
            uploaded_at=log_file.uploaded_at,
            file_hash=log_file.file_hash,
        )
        self._session.add(orm)
        await self._session.flush()  # Get the generated ID without committing

        log.info("file_saved", file_id=orm.id, filename=orm.filename)

        return _orm_to_log_file(orm)

    async def update_file_counts(
        self,
        file_id: int,
        parsed_lines: int,
        error_lines: int,
    ) -> None:
        """Update parsed/error line counts after parsing is complete."""
        result = await self._session.execute(
            select(LogFileORM).where(LogFileORM.id == file_id),
        )
        orm = result.scalar_one()
        orm.parsed_lines = parsed_lines
        orm.error_lines = error_lines
        await self._session.flush()

    async def save_entries(self, entries: list[LogEntry], log_file_id: int) -> int:
        """Save log entries in bulk using batch insert.

        Args:
            entries: List of domain LogEntry objects.
            log_file_id: FK to the parent log file.

        Returns:
            Number of entries saved.
        """
        if not entries:
            return 0

        # Convert domain models to ORM dicts for bulk insert
        orm_dicts = [
            {
                "log_file_id": log_file_id,
                "remote_addr": e.remote_addr,
                "time_local": e.time_local,
                "method": e.method,
                "path": e.path,
                "status": e.status,
                "body_bytes_sent": e.body_bytes_sent,
                "http_referer": e.http_referer,
                "http_user_agent": e.http_user_agent,
                "request_time": e.request_time,
                "source_file": e.source_file,
                "source_line": e.source_line,
                "raw_line": e.raw_line,
            }
            for e in entries
        ]

        # Bulk insert is much faster than adding one by one
        await self._session.execute(
            insert(LogEntryORM),
            orm_dicts,
        )

        log.info("entries_saved", count=len(orm_dicts), log_file_id=log_file_id)
        return len(orm_dicts)

    async def get_file(self, file_id: int) -> LogFile | None:
        """Get log file by ID."""
        result = await self._session.execute(select(LogFileORM).where(LogFileORM.id == file_id))
        orm = result.scalar_one_or_none()
        return _orm_to_log_file(orm) if orm else None

    async def list_files(self) -> list[LogFile]:
        """List all uploaded log files, newest first."""
        result = await self._session.execute(
            select(LogFileORM).order_by(LogFileORM.uploaded_at.desc())
        )
        return [_orm_to_log_file(orm) for orm in result.scalars()]

    async def get_entries(
        self,
        log_file_id: int,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[LogEntry]:
        """Get log entries for a file with pagination."""
        result = await self._session.execute(
            select(LogEntryORM)
            .where(LogEntryORM.log_file_id == log_file_id)
            .order_by(LogEntryORM.source_line)
            .limit(limit)
            .offset(offset)
        )
        return [_orm_to_log_entry(orm) for orm in result.scalars()]

    async def file_exists_by_hash(self, file_hash: str) -> bool:
        """Check if a file with this hash already exists."""
        result = await self._session.execute(
            select(func.count()).select_from(LogFileORM).where(LogFileORM.file_hash == file_hash)
        )
        count = result.scalar_one()
        return count > 0

    async def get_entry_count(self, log_file_id: int) -> int:
        """Get total entry count for a file."""
        result = await self._session.execute(
            select(func.count())
            .select_from(LogEntryORM)
            .where(LogEntryORM.log_file_id == log_file_id)
        )
        return result.scalar_one()

    async def get_status_distribution(self, log_file_id: int) -> dict[int, int]:
        """Get status code distribution for a file."""
        result = await self._session.execute(
            select(LogEntryORM.status, func.count())
            .where(LogEntryORM.log_file_id == log_file_id)
            .group_by(LogEntryORM.status)
        )
        return {int(row[0]): int(row[1]) for row in result.all()}

    async def get_top_endpoints(self, log_file_id: int, limit: int = 10) -> list[tuple[str, int]]:
        """Get most requested endpoints."""
        result = await self._session.execute(
            select(LogEntryORM.path, func.count().label("cnt"))
            .where(LogEntryORM.log_file_id == log_file_id)
            .group_by(LogEntryORM.path)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [(row[0], row[1]) for row in result.all()]

    async def get_response_times(self, log_file_id: int) -> list[float]:
        """Get all non-null response times for statistical calculations."""
        result = await self._session.execute(
            select(LogEntryORM.request_time)
            .where(
                LogEntryORM.log_file_id == log_file_id,
                LogEntryORM.request_time.is_not(None),
            )
            .order_by(LogEntryORM.request_time)
        )
        return [row[0] for row in result.all() if row[0] is not None]

    async def get_url_stats(self, log_file_id: int, limit: int = 1000) -> list[dict[str, object]]:
        """Get per-URL aggregated statistics.

        Returns list of dicts with keys: path, count, time_sum, time_avg,
        time_max. Sorted by time_sum descending.
        """
        result = await self._session.execute(
            select(
                LogEntryORM.path,
                func.count().label("count"),
                func.sum(LogEntryORM.request_time).label("time_sum"),
                func.avg(LogEntryORM.request_time).label("time_avg"),
                func.max(LogEntryORM.request_time).label("time_max"),
            )
            .where(
                LogEntryORM.log_file_id == log_file_id,
                LogEntryORM.request_time.is_not(None),
            )
            .group_by(LogEntryORM.path)
            .order_by(func.sum(LogEntryORM.request_time).desc())
            .limit(limit)
        )
        return [
            {
                "path": row[0],
                "count": int(row[1]),
                "time_sum": float(row[2]) if row[2] else 0.0,
                "time_avg": float(row[3]) if row[3] else 0.0,
                "time_max": float(row[4]) if row[4] else 0.0,
            }
            for row in result.all()
        ]

    async def get_response_times_by_path(
        self, log_file_id: int, paths: list[str]
    ) -> dict[str, list[float]]:
        """Get response times grouped by path for median calculation."""
        result = await self._session.execute(
            select(LogEntryORM.path, LogEntryORM.request_time)
            .where(
                LogEntryORM.log_file_id == log_file_id,
                LogEntryORM.request_time.is_not(None),
                LogEntryORM.path.in_(paths),
            )
            .order_by(LogEntryORM.path, LogEntryORM.request_time)
        )
        grouped: dict[str, list[float]] = {}
        for row in result.all():
            path = row[0]
            if path not in grouped:
                grouped[path] = []
            grouped[path].append(float(row[1]))
        return grouped

    async def delete_file(self, file_id: int) -> bool:
        """Delete a log file and all its entries.

        Deletes entries first (children), then the file record.

        Returns:
            True if file existed and was deleted, False otherwise.
        """
        # Check file exists
        result = await self._session.execute(select(LogFileORM).where(LogFileORM.id == file_id))
        orm = result.scalar_one_or_none()
        if orm is None:
            return False

        # Delete child entries first
        await self._session.execute(delete(LogEntryORM).where(LogEntryORM.log_file_id == file_id))

        # Delete file record
        await self._session.delete(orm)
        await self._session.flush()

        log.info("file_deleted", file_id=file_id, filename=orm.filename)
        return True


# ── Conversion helpers ────────────────────────────────


def _orm_to_log_file(orm: LogFileORM) -> LogFile:
    """Convert ORM model to domain dataclass."""
    return LogFile(
        id=orm.id,
        filename=orm.filename,
        format_name=orm.format_name,
        total_lines=orm.total_lines,
        parsed_lines=orm.parsed_lines,
        error_lines=orm.error_lines,
        uploaded_at=orm.uploaded_at,
        file_hash=orm.file_hash,
    )


def _orm_to_log_entry(orm: LogEntryORM) -> LogEntry:
    """Convert ORM model to domain dataclass."""
    return LogEntry(
        remote_addr=orm.remote_addr,
        time_local=orm.time_local
        if orm.time_local.tzinfo
        else orm.time_local.replace(
            tzinfo=UTC,
        ),
        method=orm.method,
        path=orm.path,
        status=orm.status,
        body_bytes_sent=orm.body_bytes_sent,
        http_referer=orm.http_referer,
        http_user_agent=orm.http_user_agent,
        request_time=orm.request_time,
        source_file=orm.source_file,
        source_line=orm.source_line,
        raw_line=orm.raw_line,
    )
