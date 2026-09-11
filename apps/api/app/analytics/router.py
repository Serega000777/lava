from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.schemas import AdminMetrics, QueueMetrics, SellerListingMetrics
from app.analytics.service import admin_metrics, queue_metrics, seller_metrics
from app.auth.dependencies import current_user, get_db, require_permission
from app.models import User
from app.config import settings

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/seller", response_model=list[SellerListingMetrics])
async def seller(
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    return await seller_metrics(db, user.id, limit, offset)


@router.get("/admin", response_model=AdminMetrics)
async def admin(
    _: User = Depends(require_permission("analytics:admin")),
    db: AsyncSession = Depends(get_db),
):
    return await admin_metrics(db)


@router.get("/admin/queue", response_model=QueueMetrics)
async def admin_queue(
    _: User = Depends(require_permission("analytics:admin")),
    db: AsyncSession = Depends(get_db),
):
    heartbeat: int | None = None
    redis = Redis.from_url(settings.redis_url)
    try:
        value = await redis.get("lava:worker:heartbeat")
        heartbeat = int(value) if value is not None else None
    except (RedisError, ValueError):
        heartbeat = None
    finally:
        await redis.aclose()
    return await queue_metrics(db, heartbeat)
