#!/bin/sh
# Startup script: run Alembic migrations, then start Uvicorn.
#
# This ensures the DB schema is always up-to-date when the
# backend container starts. `upgrade head` is idempotent —
# if already at latest revision, it does nothing.

set -e

echo "Running Alembic migrations..."
uv run alembic upgrade head

echo "Starting Uvicorn..."
exec uv run uvicorn log_analyzer.api.app:create_app \
    --factory \
    --host 0.0.0.0 \
    --port 8000
