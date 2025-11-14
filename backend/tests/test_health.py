import os

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_cors_headers():
    """Test that CORS headers are included in the /health response."""
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_health_cors_preflight():
    """Test dass OPTIONS-Preflight-Request korrekt beantwortet wird."""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "access-control-allow-methods" in response.headers


def test_cors_allowed_origins():
    """Test that configured origins are accepted."""
    # Read origins from .env (or use default if not set)
    allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(
        ","
    )
    allowed_origins = [o.strip() for o in allowed_origins_env]

    # At least localhost:3000 should always be present
    assert "http://localhost:3000" in allowed_origins

    # Test all configured origins
    for origin in allowed_origins:
        response = client.get(
            "/health",
            headers={"Origin": origin},
        )
        assert response.status_code == 200, f"Failed for origin: {origin}"
        assert (
            response.headers.get("access-control-allow-origin") == origin
        ), f"CORS header missing or wrong for origin: {origin}"
