import asyncio
import uuid

from fastapi import APIRouter, Depends, File, Response, UploadFile
from botocore.exceptions import ClientError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.auth.dependencies import current_user, get_db
from app.listings.service import owned_listing
from app.media.schemas import MediaResponse
from app.media.service import (
    OUTPUT_CONTENT_TYPE,
    next_position,
    normalize_image,
    public_media,
    read_limited,
)
from app.media.storage import S3Storage
from app.models import Listing, ListingMedia, User

router = APIRouter(tags=["media"])
logger = structlog.get_logger("lava.media")


@router.post("/listings/{listing_id}/media", response_model=MediaResponse, status_code=201)
async def upload_media(
    listing_id: uuid.UUID,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> ListingMedia:
    listing = await owned_listing(db, listing_id, user.id)
    if listing.status != "draft":
        from fastapi import HTTPException
        raise HTTPException(409, detail={"code": "listing_not_editable"})
    await db.execute(
        select(Listing.id).where(Listing.id == listing.id).with_for_update()
    )
    position = await next_position(db, listing.id)
    raw = await read_limited(file)
    image = await asyncio.to_thread(normalize_image, raw)
    media_id = uuid.uuid4()
    object_key = f"listings/{listing.id}/{media_id}.webp"
    storage = S3Storage()
    await asyncio.to_thread(storage.put, object_key, image.content, OUTPUT_CONTENT_TYPE)
    media = ListingMedia(
        id=media_id,
        listing_id=listing.id,
        object_key=object_key,
        content_type=OUTPUT_CONTENT_TYPE,
        size_bytes=len(image.content),
        width=image.width,
        height=image.height,
        position=position,
    )
    db.add(media)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        try:
            await asyncio.to_thread(storage.delete, object_key)
        except ClientError:
            logger.exception("orphaned_media_object", object_key=object_key)
        raise
    await db.refresh(media)
    return media


@router.get("/listings/{listing_id}/media", response_model=list[MediaResponse])
async def list_owned_media(
    listing_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ListingMedia]:
    listing = await owned_listing(db, listing_id, user.id)
    return list((await db.scalars(
        select(ListingMedia)
        .where(ListingMedia.listing_id == listing.id)
        .order_by(ListingMedia.position)
    )).all())


@router.delete("/listings/{listing_id}/media/{media_id}", status_code=204)
async def delete_media(
    listing_id: uuid.UUID,
    media_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    listing = await owned_listing(db, listing_id, user.id)
    if listing.status != "draft":
        from fastapi import HTTPException
        raise HTTPException(409, detail={"code": "listing_not_editable"})
    media = await db.scalar(select(ListingMedia).where(
        ListingMedia.id == media_id, ListingMedia.listing_id == listing.id
    ))
    if media is None:
        from fastapi import HTTPException
        raise HTTPException(404, detail={"code": "media_not_found"})
    await db.delete(media)
    await db.commit()
    try:
        await asyncio.to_thread(S3Storage().delete, media.object_key)
    except ClientError:
        logger.exception("orphaned_media_object", object_key=media.object_key)
    return Response(status_code=204)


@router.get("/media/{media_id}")
async def get_public_media(
    media_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    media = await public_media(db, media_id)
    content = await asyncio.to_thread(S3Storage().get, media.object_key)
    return Response(
        content=content,
        media_type=media.content_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
