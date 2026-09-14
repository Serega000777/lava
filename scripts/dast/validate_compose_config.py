"""Fail closed when Compose resolves different credentials for API dependencies."""

from __future__ import annotations

import hmac
import json
import sys
from typing import Any
from urllib.parse import unquote, urlparse


def _environment(service: object, name: str) -> dict[str, str]:
    if not isinstance(service, dict):
        raise TypeError(f"Compose service {name!r} is missing")
    environment = service.get("environment")
    if not isinstance(environment, dict):
        raise TypeError(f"Compose service {name!r} has no resolved environment")
    if not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in environment.items()
    ):
        raise ValueError(f"Compose service {name!r} has invalid environment values")
    return environment


def validate_compose_config(config: object) -> None:
    if not isinstance(config, dict) or not isinstance(config.get("services"), dict):
        raise TypeError("Compose configuration has no services")

    services: dict[str, Any] = config["services"]
    api = _environment(services.get("api"), "api")
    postgres = _environment(services.get("postgres"), "postgres")
    minio = _environment(services.get("minio"), "minio")

    parsed = urlparse(api.get("DATABASE_URL", ""))
    if (
        parsed.scheme != "postgresql+asyncpg"
        or parsed.hostname != "postgres"
        or parsed.port != 5432
    ):
        raise ValueError("API database URL does not target the isolated Postgres service")
    if parsed.username != postgres.get("POSTGRES_USER"):
        raise ValueError("API and Postgres database users differ")
    if parsed.path.removeprefix("/") != postgres.get("POSTGRES_DB"):
        raise ValueError("API and Postgres database names differ")

    api_password = unquote(parsed.password or "")
    postgres_password = postgres.get("POSTGRES_PASSWORD", "")
    if not api_password or not hmac.compare_digest(api_password, postgres_password):
        raise ValueError("API and Postgres passwords differ")

    for api_key, minio_key in (
        ("S3_ACCESS_KEY", "MINIO_ROOT_USER"),
        ("S3_SECRET_KEY", "MINIO_ROOT_PASSWORD"),
    ):
        api_value = api.get(api_key, "")
        minio_value = minio.get(minio_key, "")
        if not api_value or not hmac.compare_digest(api_value, minio_value):
            raise ValueError("API and object-storage credentials differ")


def main() -> None:
    try:
        validate_compose_config(json.load(sys.stdin))
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise SystemExit(f"Invalid isolated Compose configuration: {exc}") from exc
    print("Isolated Compose credentials are consistent.")


if __name__ == "__main__":
    main()
