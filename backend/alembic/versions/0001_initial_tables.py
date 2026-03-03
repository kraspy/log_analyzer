"""Initial tables — log_files and log_entries.

Revision ID: 0001
Revises:
Create Date: 2026-03-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create log_files and log_entries tables."""
    # -- log_files --
    op.create_table(
        "log_files",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("format_name", sa.String(50), nullable=False),
        sa.Column("total_lines", sa.Integer, nullable=False, server_default="0"),
        sa.Column("parsed_lines", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_lines", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("file_hash", sa.String(64), nullable=False, unique=True),
    )
    op.create_index("ix_log_files_file_hash", "log_files", ["file_hash"])

    # -- log_entries --
    op.create_table(
        "log_entries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("log_file_id", sa.Integer, nullable=False),
        # Request data
        sa.Column("remote_addr", sa.String(45), nullable=False),
        sa.Column("time_local", sa.DateTime(timezone=True), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("path", sa.Text, nullable=False),
        sa.Column("status", sa.Integer, nullable=False),
        sa.Column("body_bytes_sent", sa.Integer, nullable=False),
        sa.Column("http_referer", sa.Text, nullable=False, server_default="-"),
        sa.Column("http_user_agent", sa.Text, nullable=False, server_default=""),
        sa.Column("request_time", sa.Float, nullable=True),
        # Source traceability
        sa.Column("source_file", sa.String(500), nullable=False),
        sa.Column("source_line", sa.Integer, nullable=False),
        sa.Column("raw_line", sa.Text, nullable=False),
    )
    op.create_index("ix_log_entries_log_file_id", "log_entries", ["log_file_id"])
    op.create_index("ix_entries_file_status", "log_entries", ["log_file_id", "status"])
    op.create_index("ix_entries_file_time", "log_entries", ["log_file_id", "time_local"])
    op.create_index("ix_entries_path", "log_entries", ["path"])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table("log_entries")
    op.drop_table("log_files")
