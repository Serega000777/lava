import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_db
from app.search.postgres import PostgresListingSearch
from app.search.schemas import PublicListingResponse, SearchQuery, SearchResponse

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
    return SearchResponse(
        items=[PublicListingResponse.model_validate(item) for item in items],
        total=total, limit=limit, offset=offset,
    )
