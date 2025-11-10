from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_cors_headers():
    """Test dass CORS-Header in der /health Response enthalten sind."""
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
    """Test dass konfigurierte Origins akzeptiert werden."""
    allowed_origins = [
        "http://localhost:3000",
        "tauri://localhost",
        "http://192.168.2.116:3000",
    ]

    for origin in allowed_origins:
        response = client.get(
            "/health",
            headers={"Origin": origin},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin
