"""Test configuration and shared fixtures."""

import pytest
from fastapi.testclient import TestClient

from log_analyzer.api.app import create_app
from log_analyzer.config import Settings


@pytest.fixture
def test_settings() -> Settings:
    """Settings configured for testing."""
    return Settings(
        database_url="postgresql+asyncpg://test:test@localhost:5432/test_log_analyzer",
        debug=True,
        upload_dir="/tmp/test_uploads",  # noqa: S108
    )


@pytest.fixture
def client(test_settings: Settings) -> TestClient:
    """FastAPI test client with test settings."""
    app = create_app(settings=test_settings)
    return TestClient(app)
