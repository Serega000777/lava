"""Create and verify an ephemeral authenticated session for the DAST runner."""

from __future__ import annotations

import json
import os
import secrets
import sys
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_URL = os.environ.get("DAST_API_URL", "http://localhost:8000").rstrip("/")
ORIGIN = os.environ.get("DAST_ORIGIN", "http://localhost:3000")
CSRF_TOKEN = "lava-dast-double-submit"


def extract_cookie(headers: list[str], name: str) -> str:
    """Extract one named cookie from a collection of Set-Cookie headers."""
    for header in headers:
        parsed = SimpleCookie()
        parsed.load(header)
        if name in parsed:
            return parsed[name].value
    raise RuntimeError(f"response did not set required cookie {name!r}")


def request_json(
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, object], list[str]]:
    body = json.dumps(payload).encode() if payload is not None else None
    request_headers = {"Accept": "application/json", **(headers or {})}
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    request = Request(
        f"{API_URL}{path}", data=body, headers=request_headers, method=method
    )
    with urlopen(request, timeout=15) as response:
        response_body = json.load(response)
        if not isinstance(response_body, dict):
            raise TypeError(f"{path} returned a non-object JSON response")
        return response.status, response_body, response.headers.get_all("Set-Cookie", [])


def append_github_environment(cookie_header: str) -> None:
    environment_path = os.environ.get("GITHUB_ENV")
    if not environment_path:
        raise RuntimeError("GITHUB_ENV is required to pass credentials to the scanner")
    if "\n" in cookie_header:
        raise RuntimeError("refusing to write multiline credentials")

    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::add-mask::{cookie_header}")
    with Path(environment_path).open("a", encoding="utf-8", newline="\n") as output:
        output.write("ZAP_AUTH_HEADER=Cookie\n")
        output.write(f"ZAP_AUTH_HEADER_VALUE={cookie_header}\n")


def main() -> int:
    try:
        phone = os.environ.get("DAST_PHONE") or f"+7999{secrets.randbelow(10_000_000):07d}"
        password = f"Dast-{secrets.token_urlsafe(32)}-7"
        register_status, _, register_headers = request_json(
            "/auth/register/password",
            method="POST",
            payload={
                "phone": phone,
                "display_name": "Lava DAST",
                "password": password,
            },
            headers={"Origin": ORIGIN},
        )
        if register_status != 201:
            raise RuntimeError(f"registration returned HTTP {register_status}")
        session = extract_cookie(register_headers, "lava_session")
        cookie_header = f"lava_session={session}; lava_csrf={CSRF_TOKEN}"

        me_status, _, _ = request_json(
            "/me", headers={"Cookie": cookie_header, "Origin": ORIGIN}
        )
        if me_status != 200:
            raise RuntimeError(f"authenticated verification returned HTTP {me_status}")

        append_github_environment(cookie_header)
        print("Ephemeral DAST session created and verified.")
        return 0
    except (HTTPError, URLError, OSError, RuntimeError, ValueError) as error:
        print(f"DAST session bootstrap failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
