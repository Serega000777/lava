import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import current_user, get_db
from app.favorites.service import add_favorite, list_favorites, remove_favorite
from app.models import User
from app.search.schemas import PublicListingResponse

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("", response_model=list[PublicListingResponse])
async def favorites(
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PublicListingResponse]:
    listings = await list_favorites(db, user.id, limit, offset)
    return [PublicListingResponse.model_validate(listing) for listing in listings]


@router.put("/{listing_id}", status_code=204)
async def favorite(
    listing_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await add_favorite(db, user.id, listing_id)
    return Response(status_code=204)


@router.delete("/{listing_id}", status_code=204)
async def unfavorite(
    listing_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await remove_favorite(db, user.id, listing_id)
    return Response(status_code=204)
