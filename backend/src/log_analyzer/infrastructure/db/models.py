"""SQLAlchemy ORM models — database representation of domain entities.

ORM models live in Infrastructure, NOT in Domain. Domain models
are plain dataclasses — ORM models are SQLAlchemy-specific mappings.
We convert between them at the repository boundary.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class LogFileORM(Base):
    """Database table for uploaded log file metadata.

    Maps to domain model: log_analyzer.domain.models.LogFile
    """

    __tablename__ = "log_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(500))
    format_name: Mapped[str] = mapped_column(String(50))
    total_lines: Mapped[int] = mapped_column(Integer, default=0)
    parsed_lines: Mapped[int] = mapped_column(Integer, default=0)
    error_lines: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)


class LogEntryORM(Base):
    """Database table for individual log entries.

    Maps to domain model: log_analyzer.domain.models.LogEntry

    Indexes:
    - file_hash on LogFileORM for deduplication
    - (log_file_id, status) for filtering by status code
    - (log_file_id, time_local) for time-range queries
    - path for endpoint analytics
    """

    __tablename__ = "log_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    log_file_id: Mapped[int] = mapped_column(Integer, index=True)

    # Request data
    remote_addr: Mapped[str] = mapped_column(String(45))  # IPv6 max length
    time_local: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    method: Mapped[str] = mapped_column(String(10))
    path: Mapped[str] = mapped_column(Text)
    status: Mapped[int] = mapped_column(Integer)
    body_bytes_sent: Mapped[int] = mapped_column(Integer)
    http_referer: Mapped[str] = mapped_column(Text, default="-")
    http_user_agent: Mapped[str] = mapped_column(Text, default="")
    request_time: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Source traceability
    source_file: Mapped[str] = mapped_column(String(500))
    source_line: Mapped[int] = mapped_column(Integer)
    raw_line: Mapped[str] = mapped_column(Text)

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("ix_entries_file_status", "log_file_id", "status"),
        Index("ix_entries_file_time", "log_file_id", "time_local"),
        Index("ix_entries_path", "path"),
    )
