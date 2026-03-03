"""Database session management — async SQLAlchemy session factory.

Creates AsyncSession instances for database operations.
Uses async engine with asyncpg driver for non-blocking I/O.

Usage in FastAPI:
    session_factory = create_session_factory(settings.database_url)
    async with session_factory() as session:
        ...
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_session_factory(
    database_url: str,
    echo: bool = False,
) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory.

    Args:
        database_url: PostgreSQL connection string
            (e.g., "postgresql+asyncpg://user:pass@host/db").
        echo: If True, log all SQL statements (useful for debugging).

    Returns:
        Session factory that creates AsyncSession instances.
    """
    engine = create_async_engine(
        database_url,
        echo=echo,
        pool_size=10,  # Max persistent connections
        max_overflow=20,  # Extra connections under load
        pool_pre_ping=True,  # Check connection health before use
    )

    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Don't expire objects after commit (avoids lazy loads)
    )


@asynccontextmanager
async def get_session(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Context manager for database sessions.

    Automatically commits on success, rolls back on error.

    Usage:
        async with get_session(factory) as session:
            await session.execute(...)
    """
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
