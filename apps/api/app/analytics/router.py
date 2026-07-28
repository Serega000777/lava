from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.schemas import AdminMetrics, SellerListingMetrics
from app.analytics.service import admin_metrics, seller_metrics
from app.auth.dependencies import current_user, get_db, require_permission
from app.models import User

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
