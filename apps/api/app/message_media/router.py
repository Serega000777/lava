import asyncio
import uuid

import structlog
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, File, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import current_user, get_db, require_permission
from app.config import settings
from app.media.service import OUTPUT_CONTENT_TYPE, normalize_image, read_limited
from app.media.storage import S3Storage
from app.message_media.schemas import MessageMediaResponse
from app.message_media.service import (
    ensure_message_media_mutable,
    list_participant_message_media,
    moderation_media,
    next_message_media_position,
    owned_message_for_media,
    participant_media,
)
from app.models import Message, MessageMedia, User

router = APIRouter(tags=["message-media"])
logger = structlog.get_logger("lava.message_media")


@router.post("/messages/{message_id}/media", response_model=MessageMediaResponse, status_code=201)
async def upload_message_media(
    message_id: uuid.UUID,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageMedia:
    message = await owned_message_for_media(db, message_id, user.id)
    await db.execute(select(Message.id).where(Message.id == message.id).with_for_update())
    await ensure_message_media_mutable(db, message, user.id)
    position = await next_message_media_position(db, message.id)
    raw = await read_limited(file, settings.message_media_max_bytes)
    image = await asyncio.to_thread(normalize_image, raw)
    media_id = uuid.uuid4()
    object_key = f"messages/{message.id}/{media_id}.webp"
    storage = S3Storage()
    await asyncio.to_thread(
        storage.put,
        object_key,
        image.content,
        OUTPUT_CONTENT_TYPE,
        "private, no-store",
    )
    media = MessageMedia(
        id=media_id,
        message_id=message.id,
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
            logger.exception("orphaned_message_media_object", object_key=object_key)
        raise
    await db.refresh(media)
    return media


@router.get("/messages/{message_id}/media", response_model=list[MessageMediaResponse])
async def list_message_media(
    message_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageMedia]:
    return await list_participant_message_media(db, message_id, user.id)


@router.get("/message-media/{media_id}")
async def get_message_media(
    media_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    media = await participant_media(db, media_id, user.id)
    content = await asyncio.to_thread(S3Storage().get, media.object_key)
    return Response(
        content=content,
        media_type=media.content_type,
        headers={"Cache-Control": "private, no-store"},
    )


@router.get("/moderation/message-media/{media_id}")
async def get_moderation_message_media(
    media_id: uuid.UUID,
    _: User = Depends(require_permission("moderation:read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    media = await moderation_media(db, media_id)
    content = await asyncio.to_thread(S3Storage().get, media.object_key)
    return Response(
        content=content,
        media_type=media.content_type,
        headers={"Cache-Control": "private, no-store"},
    )
