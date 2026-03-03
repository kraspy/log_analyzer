"""Widen path, http_referer, http_user_agent to TEXT.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Change VARCHAR columns to TEXT to avoid truncation on long log lines."""
    op.alter_column(
        "log_entries",
        "path",
        type_=sa.Text(),
        existing_type=sa.String(2000),
        existing_nullable=False,
    )
    op.alter_column(
        "log_entries",
        "http_referer",
        type_=sa.Text(),
        existing_type=sa.String(2000),
        existing_nullable=False,
    )
    op.alter_column(
        "log_entries",
        "http_user_agent",
        type_=sa.Text(),
        existing_type=sa.String(1000),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Revert TEXT columns back to VARCHAR."""
    op.alter_column(
        "log_entries",
        "path",
        type_=sa.String(2000),
        existing_type=sa.Text(),
        existing_nullable=False,
    )
    op.alter_column(
        "log_entries",
        "http_referer",
        type_=sa.String(2000),
        existing_type=sa.Text(),
        existing_nullable=False,
    )
    op.alter_column(
        "log_entries",
        "http_user_agent",
        type_=sa.String(1000),
        existing_type=sa.Text(),
        existing_nullable=False,
    )
