import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import current_user, get_db
from app.blocking.schemas import BlockedUserResponse
from app.blocking.service import block_user, list_blocked_users, unblock_user
from app.models import User

router = APIRouter(tags=["blocking"])


@router.put("/users/{user_id}/block", response_model=BlockedUserResponse, status_code=201)
async def block(
    user_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    return await block_user(db, user.id, user_id)


@router.delete("/users/{user_id}/block", status_code=204)
async def unblock(
    user_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await unblock_user(db, user.id, user_id)


@router.get("/blocks", response_model=list[BlockedUserResponse])
async def blocks(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_blocked_users(db, user.id, limit, offset)
