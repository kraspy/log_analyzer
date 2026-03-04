# ── Build stage ──────────────────────────────────────
# Uses official uv image with Python 3.14 on Alpine
FROM ghcr.io/astral-sh/uv:python3.14.3-alpine AS builder

WORKDIR /app

# Copy workspace root + backend dependency files (Docker layer caching)
COPY pyproject.toml uv.lock ./
COPY backend/pyproject.toml backend/README.md backend/

# Install dependencies without project source (cached layer)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-workspace --no-dev --project backend

# Copy backend source code + Alembic
COPY backend/src/ backend/src/
COPY backend/alembic.ini backend/
COPY backend/alembic/ backend/alembic/

# Final sync — install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --project backend

# ── Runtime stage ────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.14.3-alpine

WORKDIR /app

# Copy everything from builder (venv + source + alembic)
COPY --from=builder /app /app

# Copy startup script into backend dir (alembic.ini expects %(here)s/alembic)
COPY backend/start.sh ./backend/start.sh
RUN chmod +x ./backend/start.sh

# Create uploads directory
RUN mkdir -p /app/uploads

# alembic.ini uses %(here)s — run from backend/
WORKDIR /app/backend

EXPOSE 8000

CMD ["./start.sh"]
