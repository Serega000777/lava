from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from pydantic import SecretStr
from pydantic import ValidationError
import pytest

from app.config import Settings, settings
from app.main import app
from app.observability import HttpMetrics


def test_metrics_endpoint_is_hidden_without_token(monkeypatch) -> None:
    monkeypatch.setattr(settings, "metrics_token", None)

    response = TestClient(app).get("/internal/metrics")

    assert response.status_code == 404


def test_metrics_token_rejects_weak_non_empty_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, metrics_token="short-token")


def test_blank_metrics_token_disables_exporter() -> None:
    configured = Settings(_env_file=None, metrics_token="")

    assert configured.metrics_token is None


def test_metrics_endpoint_is_hidden_for_wrong_token(monkeypatch) -> None:
    monkeypatch.setattr(settings, "metrics_token", SecretStr("c" * 32))

    response = TestClient(app).get(
        "/internal/metrics", headers={"Authorization": f"Bearer {'w' * 32}"}
    )

    assert response.status_code == 404


def test_authorized_metrics_are_aggregated_and_openmetrics_compatible(monkeypatch) -> None:
    metrics_token = "metrics-test-token-with-32-characters"
    monkeypatch.setattr(settings, "metrics_token", SecretStr(metrics_token))
    redis = AsyncMock()
    redis.get.return_value = b"1780000000"
    monkeypatch.setattr("app.main.Redis.from_url", lambda _url: redis)

    async def metrics_stub(_db, _heartbeat):
        return {
            "pending": 2,
            "processing": 1,
            "failed": 0,
            "completed": 7,
            "oldest_pending_seconds": 4,
            "worker_healthy": True,
            "heartbeat_age_seconds": 1,
        }

    monkeypatch.setattr("app.main.queue_metrics", metrics_stub)

    response = TestClient(app).get(
        "/internal/metrics",
        headers={"Authorization": f"Bearer {metrics_token}"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/openmetrics-text")
    assert 'lava_queue_tasks{status="pending"} 2' in response.text
    assert "lava_worker_healthy 1" in response.text
    assert response.text.endswith("# EOF\n")
    assert metrics_token not in response.text
    redis.aclose.assert_awaited_once()


def test_http_metrics_uses_route_templates_without_identifiers() -> None:
    registry = HttpMetrics()
    registry.observe("GET", "/listings/{listing_id}", 200, 0.25)

    body = registry.render(
        {
            "pending": 0,
            "processing": 0,
            "failed": 0,
            "completed": 0,
            "oldest_pending_seconds": None,
            "worker_healthy": False,
            "heartbeat_age_seconds": None,
        }
    )

    assert 'route="/listings/{listing_id}"' in body
