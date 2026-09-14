"""Create the bounded OpenAPI input used by the authenticated DAST scan."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_URL = os.environ.get("DAST_API_URL", "http://localhost:8000").rstrip("/")
OUTPUT_PATH = Path(os.environ.get("DAST_OPENAPI_PATH", ".zap/runtime/openapi.json"))
EXCLUDED_PREFIXES = ("/auth", "/internal")


class InvalidOpenApi(ValueError):
    """Raised when the source schema is missing the required OpenAPI structure."""


def is_excluded_path(path: str) -> bool:
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in EXCLUDED_PREFIXES)


def filter_schema(schema: object) -> dict[str, Any]:
    if not isinstance(schema, dict) or not isinstance(schema.get("paths"), dict):
        raise InvalidOpenApi("schema must contain a paths object")

    filtered = dict(schema)
    filtered["paths"] = {
        path: definition
        for path, definition in schema["paths"].items()
        if isinstance(path, str) and not is_excluded_path(path)
    }
    if "/me" not in filtered["paths"]:
        raise InvalidOpenApi("authenticated verification route /me is missing")
    if not filtered["paths"]:
        raise InvalidOpenApi("filtered schema contains no paths")
    return filtered


def load_schema() -> object:
    request = Request(f"{API_URL}/openapi.json", headers={"Accept": "application/json"})
    with urlopen(request, timeout=15) as response:  # noqa: S310 - fixed trusted CI URL
        if response.status != 200:
            raise InvalidOpenApi(f"OpenAPI endpoint returned HTTP {response.status}")
        return json.load(response)


def main() -> int:
    try:
        schema = filter_schema(load_schema())
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(
            json.dumps(schema, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
    except (HTTPError, URLError, OSError, json.JSONDecodeError, InvalidOpenApi) as error:
        print(f"DAST OpenAPI preparation failed: {error}", file=sys.stderr)
        return 1
    print(f"Prepared bounded DAST schema with {len(schema['paths'])} paths.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
