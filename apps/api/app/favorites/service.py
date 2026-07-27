import uuid

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Favorite, Listing


async def add_favorite(db: AsyncSession, user_id: uuid.UUID, listing_id: uuid.UUID) -> None:
    is_active = await db.scalar(
        select(Listing.id).where(Listing.id == listing_id, Listing.status == "active")
    )
    if is_active is None:
        raise HTTPException(404, detail={"code": "listing_not_found"})
    await db.execute(
        insert(Favorite)
        .values(user_id=user_id, listing_id=listing_id)
        .on_conflict_do_nothing(index_elements=["user_id", "listing_id"])
    )
    await db.commit()


async def remove_favorite(db: AsyncSession, user_id: uuid.UUID, listing_id: uuid.UUID) -> None:
    await db.execute(
        delete(Favorite).where(Favorite.user_id == user_id, Favorite.listing_id == listing_id)
    )
    await db.commit()


async def list_favorites(
    db: AsyncSession, user_id: uuid.UUID, limit: int, offset: int
) -> list[Listing]:
    return list((await db.scalars(
        select(Listing)
        .join(Favorite, Favorite.listing_id == Listing.id)
        .where(Favorite.user_id == user_id, Listing.status == "active")
        .order_by(Favorite.created_at.desc(), Listing.id)
        .limit(limit)
        .offset(offset)
    )).all())
