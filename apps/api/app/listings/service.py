import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.listings.schemas import ListingCreate, ListingUpdate
from app.models import Category, CategoryAttribute, Listing, ModerationCase


async def create_draft(db: AsyncSession, owner_id: uuid.UUID, data: ListingCreate) -> Listing:
    if not await db.get(Category, data.category_id):
        raise HTTPException(422, detail={"code": "invalid_category"})
    listing = Listing(owner_id=owner_id, **data.model_dump())
    db.add(listing)
    await db.commit()
    await db.refresh(listing)
    return listing


async def owned_listing(db: AsyncSession, listing_id: uuid.UUID, owner_id: uuid.UUID) -> Listing:
    listing = await db.scalar(
        select(Listing).where(Listing.id == listing_id, Listing.owner_id == owner_id)
    )
    if not listing:
        raise HTTPException(404, detail={"code": "listing_not_found"})
    return listing


async def update_draft(db: AsyncSession, listing: Listing, data: ListingUpdate) -> Listing:
    if listing.status != "draft":
        raise HTTPException(409, detail={"code": "listing_not_editable"})
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(listing, key, value)
    await db.commit()
    await db.refresh(listing)
    return listing


async def submit_draft(db: AsyncSession, listing: Listing) -> Listing:
    if listing.status != "draft":
        raise HTTPException(409, detail={"code": "invalid_listing_status"})
    required = (
        await db.scalars(
            select(CategoryAttribute).where(
                CategoryAttribute.category_id == listing.category_id,
                CategoryAttribute.is_required.is_(True),
            )
        )
    ).all()
    missing = [attribute.key for attribute in required if listing.attributes.get(attribute.key) in (None, "")]
    missing_fields = ([] if listing.description.strip() else ["description"]) + missing
    if missing_fields:
        raise HTTPException(
            422,
            detail={"code": "listing_incomplete", "missing_fields": missing_fields},
        )
    listing.status = "pending_moderation"
    db.add(ModerationCase(listing_id=listing.id))
    await db.commit()
    await db.refresh(listing)
    return listing
