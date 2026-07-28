import hashlib
import secrets

from fastapi import Request
from redis.asyncio import Redis

from app.config import settings

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
RATE_LIMITED_AUTH_PATHS = frozenset({
    "/auth/register/password",
    "/auth/login/password",
    "/auth/otp/request",
    "/auth/otp/verify",
})


def csrf_is_valid(request: Request) -> bool:
    cookie = request.cookies.get("lava_csrf")
    header = request.headers.get("x-csrf-token")
    return bool(cookie and header and secrets.compare_digest(cookie, header))


def origin_is_allowed(request: Request) -> bool:
    origin = request.headers.get("origin")
    return origin is None or origin in settings.cors_origins


async def auth_rate_limit_exceeded(request: Request) -> bool:
    if request.url.path not in RATE_LIMITED_AUTH_PATHS:
        return False
    client = request.client.host if request.client else "unknown"
    identity = hashlib.sha256(f"{client}:{request.url.path}".encode()).hexdigest()
    key = f"rate:auth:{identity}"
    redis = Redis.from_url(settings.redis_url)
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, settings.auth_rate_window_seconds)
        return count > settings.auth_rate_limit
    finally:
        await redis.aclose()
