import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_db
from app.search.postgres import PostgresListingSearch
from app.search.schemas import PublicListingResponse, SearchQuery, SearchResponse
from app.models import ListingMedia

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
    return SearchResponse(
        items=[
            PublicListingResponse.model_validate(item).model_copy(
                update={"cover_image_url": covers.get(item.id)}
            )
            for item in items
        ],
        total=total, limit=limit, offset=offset,
    )
