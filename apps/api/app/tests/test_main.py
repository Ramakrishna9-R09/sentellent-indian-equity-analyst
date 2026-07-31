from fastapi.testclient import TestClient

from app.main import app


def test_health_route_starts_without_database() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api"}


def test_health_route_returns_json() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.headers["content-type"] == "application/json"


def test_cors_headers_present() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert response.status_code == 200


def test_nonexistent_route_returns_404() -> None:
    with TestClient(app) as client:
        response = client.get("/api/nonexistent")
    assert response.status_code == 404
