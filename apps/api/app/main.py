from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from sqlalchemy import text

from app.config import settings
from app.db import session_factory
from app.auth.router import router as auth_router
from app.listings.router import router as listings_router
from app.moderation.router import router as moderation_router
from app.search.router import router as search_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="Lava API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type"],
)
app.include_router(auth_router)
app.include_router(listings_router)
app.include_router(moderation_router)
app.include_router(search_router)


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
