import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_db
from app.search.postgres import PostgresListingSearch
from app.search.schemas import PublicListingResponse, SearchQuery, SearchResponse
from app.models import ListingMedia, User
from app.verification.service import trust_badge

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/listings", response_model=SearchResponse)
async def search_listings(
    q: str = Query(default="", max_length=200),
    category_id: uuid.UUID | None = None,
    city: str | None = Query(default=None, max_length=120),
    price_min: Decimal | None = Query(default=None, ge=0),
    price_max: Decimal | None = Query(default=None, ge=0),
    sort: str = Query(default="relevance", pattern=r"^(relevance|newest|price_asc|price_desc)$"),
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    query = SearchQuery(
        q=q, category_id=category_id, city=city, price_min=price_min,
        price_max=price_max, sort=sort, limit=limit, offset=offset,
    )
    items, total = await PostgresListingSearch(db).search(query)
    listing_ids = [item.id for item in items]
    media = [] if not listing_ids else list((await db.scalars(
        select(ListingMedia)
        .where(ListingMedia.listing_id.in_(listing_ids))
        .order_by(ListingMedia.listing_id, ListingMedia.position)
    )).all())
    covers: dict[uuid.UUID, str] = {}
    for item in media:
        covers.setdefault(item.listing_id, f"/media/{item.id}")
    owner_ids = {item.owner_id for item in items}
    owners = {} if not owner_ids else {
        owner.id: owner
        for owner in (await db.scalars(select(User).where(User.id.in_(owner_ids)))).all()
    }
    return SearchResponse(
        items=[
            PublicListingResponse.model_validate(item).model_copy(
                update={
                    "cover_image_url": covers.get(item.id),
                    "seller_id": item.owner_id,
                    "seller_name": owners[item.owner_id].display_name if item.owner_id in owners else None,
                    "seller_trust_badge": (
                        trust_badge(
                            owners[item.owner_id].verification_level,
                            owners[item.owner_id].role,
                        )
                        if item.owner_id in owners else None
                    ),
                }
            )
            for item in items
        ],
        total=total, limit=limit, offset=offset,
    )
