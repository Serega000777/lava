import secrets
import threading
from collections import Counter

from fastapi import Request
from pydantic import SecretStr


class HttpMetrics:
    def __init__(self) -> None:
        self._requests: Counter[tuple[str, str, int]] = Counter()
        self._duration_seconds: Counter[tuple[str, str]] = Counter()
        self._lock = threading.Lock()

    def observe(self, method: str, route: str, status: int, duration_seconds: float) -> None:
        with self._lock:
            self._requests[(method, route, status)] += 1
            self._duration_seconds[(method, route)] += duration_seconds

    def render(self, queue: dict[str, int | bool | None]) -> str:
        lines = [
            "# HELP lava_http_requests_total HTTP requests processed.",
            "# TYPE lava_http_requests_total counter",
        ]
        with self._lock:
            requests = sorted(self._requests.items())
            durations = sorted(self._duration_seconds.items())
        for (method, route, status), value in requests:
            lines.append(
                f'lava_http_requests_total{{method="{method}",route="{route}",status="{status}"}} {value}'
            )
        lines.extend(
            [
                "# HELP lava_http_request_duration_seconds_sum Total HTTP request duration.",
                "# TYPE lava_http_request_duration_seconds_sum counter",
            ]
        )
        for (method, route), value in durations:
            lines.append(
                f'lava_http_request_duration_seconds_sum{{method="{method}",route="{route}"}} {value:.6f}'
            )
        for status in ("pending", "processing", "failed", "completed"):
            lines.append(f'lava_queue_tasks{{status="{status}"}} {int(queue[status])}')
        oldest = queue["oldest_pending_seconds"]
        lines.append(f"lava_queue_oldest_pending_seconds {int(oldest) if oldest is not None else 0}")
        lines.append(f"lava_worker_healthy {1 if queue['worker_healthy'] else 0}")
        lines.append("# EOF")
        return "\n".join(lines) + "\n"


def metrics_request_is_authorized(request: Request, token: SecretStr | None) -> bool:
    if token is None:
        return False
    authorization = request.headers.get("authorization", "")
    scheme, separator, supplied = authorization.partition(" ")
    return bool(
        separator
        and scheme.lower() == "bearer"
        and supplied
        and secrets.compare_digest(supplied, token.get_secret_value())
    )


http_metrics = HttpMetrics()
