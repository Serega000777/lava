from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError

from app.main import app


def test_api_adds_request_and_security_headers() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"


def test_authenticated_mutation_requires_csrf_token() -> None:
    client = TestClient(app)
    client.cookies.set("lava_session", "session")
    response = client.post("/health")
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "csrf_invalid"


def test_csrf_double_submit_allows_matching_token() -> None:
    client = TestClient(app)
    token = client.get("/auth/csrf").json()["token"]
    client.cookies.set("lava_session", "session")
    response = client.post("/health", headers={"X-CSRF-Token": token})
    assert response.status_code == 405


def test_cross_origin_mutation_is_rejected() -> None:
    response = TestClient(app).post(
        "/auth/login/password",
        headers={"Origin": "https://evil.example"},
        json={"phone": "+79990000000", "password": "StrongPass123"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "origin_not_allowed"


def test_auth_fails_closed_when_rate_limiter_is_unavailable(monkeypatch) -> None:
    async def unavailable(_request) -> bool:
        raise RedisConnectionError("redis unavailable")

    monkeypatch.setattr("app.main.auth_rate_limit_exceeded", unavailable)
    response = TestClient(app).post(
        "/auth/login/password",
        json={"phone": "+79990000000", "password": "StrongPass123"},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "security_dependency_unavailable"
