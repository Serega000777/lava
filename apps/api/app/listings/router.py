import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import current_user, get_db
from app.listings.schemas import (
    AttributeResponse,
    CategoryResponse,
    ListingCreate,
    ListingResponse,
    ListingUpdate,
)
from app.listings.service import create_draft, owned_listing, submit_draft, update_draft
from app.models import Category, CategoryAttribute, Listing, User

router = APIRouter()


@router.get("/categories", response_model=list[CategoryResponse])
async def categories(db: AsyncSession = Depends(get_db)) -> list[CategoryResponse]:
    result = (await db.scalars(select(Category).order_by(Category.name))).all()
    response = []
    for category in result:
        attrs = (
            await db.scalars(
                select(CategoryAttribute)
                .where(CategoryAttribute.category_id == category.id)
                .order_by(CategoryAttribute.label)
            )
        ).all()
        response.append(CategoryResponse(
            id=category.id, slug=category.slug, name=category.name,
            attributes=[AttributeResponse.model_validate(attr) for attr in attrs],
        ))
    return response


@router.post("/listings", response_model=ListingResponse, status_code=201)
async def create_listing(
    data: ListingCreate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> Listing:
    return await create_draft(db, user.id, data)


@router.get("/listings/mine", response_model=list[ListingResponse])
async def my_listings(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> list[Listing]:
    return list((await db.scalars(
        select(Listing).where(Listing.owner_id == user.id).order_by(Listing.updated_at.desc())
    )).all())


@router.get("/listings/{listing_id}", response_model=ListingResponse)
async def get_listing(
    listing_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> Listing:
    return await owned_listing(db, listing_id, user.id)


@router.patch("/listings/{listing_id}", response_model=ListingResponse)
async def patch_listing(
    listing_id: uuid.UUID, data: ListingUpdate, user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> Listing:
    return await update_draft(db, await owned_listing(db, listing_id, user.id), data)


@router.post("/listings/{listing_id}/submit", response_model=ListingResponse)
async def submit_listing(
    listing_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> Listing:
    return await submit_draft(db, await owned_listing(db, listing_id, user.id))


@router.delete("/listings/{listing_id}", status_code=204)
async def delete_listing(
    listing_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> Response:
    listing = await owned_listing(db, listing_id, user.id)
    if listing.status != "draft":
        from fastapi import HTTPException
        raise HTTPException(409, detail={"code": "listing_not_deletable"})
    await db.delete(listing)
    await db.commit()
    return Response(status_code=204)

