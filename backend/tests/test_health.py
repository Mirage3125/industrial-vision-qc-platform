from fastapi.testclient import TestClient


def test_health_returns_standard_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "test-request"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request"
    assert response.json() == {
        "success": True,
        "data": {
            "status": "healthy",
            "service": "Factory Vision Quality Loop",
            "environment": "development",
            "database": None,
        },
        "error": None,
        "request_id": "test-request",
    }


def test_ready_checks_database(client: TestClient) -> None:
    response = client.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json()["data"]["database"] == "reachable"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
