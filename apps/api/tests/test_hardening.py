from fastapi.testclient import TestClient

from app.main import app


def test_api_adds_request_and_security_headers() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
