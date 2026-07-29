import uuid
from dataclasses import dataclass
from io import BytesIO

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Listing, ListingMedia

ALLOWED_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})
OUTPUT_CONTENT_TYPE = "image/webp"


@dataclass(frozen=True)
class NormalizedImage:
    content: bytes
    width: int
    height: int


def normalize_image(raw: bytes) -> NormalizedImage:
    if not raw:
        raise HTTPException(422, detail={"code": "empty_media"})
    try:
        with Image.open(BytesIO(raw)) as source:
            if source.format not in ALLOWED_FORMATS:
                raise HTTPException(415, detail={"code": "unsupported_media_type"})
            if source.width * source.height > settings.media_max_pixels:
                raise HTTPException(413, detail={"code": "image_dimensions_too_large"})
            source.verify()
        with Image.open(BytesIO(raw)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((4096, 4096))
            output = BytesIO()
            image.save(output, format="WEBP", quality=85, method=6)
            return NormalizedImage(output.getvalue(), image.width, image.height)
    except HTTPException:
        raise
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as error:
        raise HTTPException(422, detail={"code": "invalid_image"}) from error


async def read_limited(upload: UploadFile) -> bytes:
    raw = await upload.read(settings.media_max_bytes + 1)
    if len(raw) > settings.media_max_bytes:
        raise HTTPException(413, detail={"code": "media_too_large"})
    return raw


def first_available_position(positions: list[int]) -> int:
    occupied = set(positions)
    for position in range(settings.media_max_per_listing):
        if position not in occupied:
            return position
    raise HTTPException(409, detail={"code": "media_limit_reached"})


async def next_position(db: AsyncSession, listing_id: uuid.UUID) -> int:
    positions = list((await db.scalars(
        select(ListingMedia.position).where(ListingMedia.listing_id == listing_id)
    )).all())
    if len(positions) >= settings.media_max_per_listing:
        raise HTTPException(409, detail={"code": "media_limit_reached"})
    return first_available_position(positions)


async def public_media(db: AsyncSession, media_id: uuid.UUID) -> ListingMedia:
    media = await db.scalar(
        select(ListingMedia)
        .join(Listing)
        .where(ListingMedia.id == media_id, Listing.status == "active")
    )
    if media is None:
        raise HTTPException(404, detail={"code": "media_not_found"})
    return media
