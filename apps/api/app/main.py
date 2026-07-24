from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis
from sqlalchemy import text

from app.config import settings
from app.db import session_factory


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="Lava API", version="0.1.0", lifespan=lifespan)


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

