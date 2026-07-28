from contextlib import asynccontextmanager
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
import structlog

from app.config import settings
from app.db import session_factory
from app.auth.router import router as auth_router
from app.listings.router import router as listings_router
from app.moderation.router import router as moderation_router
from app.search.router import router as search_router
from app.favorites.router import router as favorites_router
from app.messaging.router import router as messaging_router
from app.reviews.router import router as reviews_router
from app.ai.router import router as ai_router
from app.analytics.router import router as analytics_router
from app.security import (
    UNSAFE_METHODS,
    auth_rate_limit_exceeded,
    csrf_is_valid,
    origin_is_allowed,
)

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger("lava.api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="Lava API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)
app.include_router(auth_router)
app.include_router(listings_router)
app.include_router(moderation_router)
app.include_router(search_router)
app.include_router(favorites_router)
app.include_router(messaging_router)
app.include_router(reviews_router)
app.include_router(ai_router)
app.include_router(analytics_router)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = str(uuid.uuid4())
    started = time.perf_counter()
    if request.method in UNSAFE_METHODS and not origin_is_allowed(request):
        response = JSONResponse(
            status_code=403, content={"detail": {"code": "origin_not_allowed"}}
        )
    elif (
        request.method in UNSAFE_METHODS
        and request.cookies.get("lava_session")
        and not csrf_is_valid(request)
    ):
        response = JSONResponse(
            status_code=403, content={"detail": {"code": "csrf_invalid"}}
        )
    else:
        try:
            rate_limited = await auth_rate_limit_exceeded(request)
        except RedisError:
            logger.exception(
                "auth_rate_limit_unavailable",
                request_id=request_id,
                path=request.url.path,
            )
            response = JSONResponse(
                status_code=503,
                content={"detail": {"code": "security_dependency_unavailable"}},
            )
        else:
            if rate_limited:
                response = JSONResponse(
                    status_code=429,
                    content={"detail": {"code": "rate_limited"}},
                    headers={"Retry-After": str(settings.auth_rate_window_seconds)},
                )
            else:
                response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    logger.info(
        "request_completed",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
    )
    return response


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "lava-api"}


@app.get("/ready", tags=["system"])
async def readiness() -> dict[str, str]:
    async with session_factory() as session:
        await session.execute(text("SELECT 1"))
    redis = Redis.from_url(settings.redis_url)
    try:
        await redis.ping()
    finally:
        await redis.aclose()
    return {"status": "ready"}
