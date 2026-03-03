"""Smoke tests — verify the app starts and health check works."""

from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """Health endpoint should return 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_schema(client: TestClient) -> None:
    """OpenAPI schema should be accessible."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "LOG Analyzer API"
