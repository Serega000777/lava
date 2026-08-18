import uuid

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.blocking.service import ensure_messaging_allowed
from app.models import Conversation, Message, MessageMedia, MessageReport


async def owned_message_for_media(
    db: AsyncSession, message_id: uuid.UUID, user_id: uuid.UUID
) -> Message:
    message = await db.scalar(
        select(Message).where(Message.id == message_id, Message.sender_id == user_id)
    )
    if message is None:
        raise HTTPException(404, detail={"code": "message_not_found"})
    return message


async def ensure_message_media_mutable(
    db: AsyncSession, message: Message, user_id: uuid.UUID
) -> None:
    conversation = await db.get(Conversation, message.conversation_id)
    if conversation is None:
        raise HTTPException(404, detail={"code": "message_not_found"})
    recipient_id = (
        conversation.seller_id if user_id == conversation.buyer_id else conversation.buyer_id
    )
    await ensure_messaging_allowed(db, user_id, recipient_id)
    reported = await db.scalar(
        select(MessageReport.id).where(MessageReport.message_id == message.id).limit(1)
    )
    if reported is not None:
        raise HTTPException(409, detail={"code": "reported_message_media_locked"})


async def next_message_media_position(db: AsyncSession, message_id: uuid.UUID) -> int:
    positions = set(
        (
            await db.scalars(
                select(MessageMedia.position).where(MessageMedia.message_id == message_id)
            )
        ).all()
    )
    for position in range(settings.message_media_max_per_message):
        if position not in positions:
            return position
    raise HTTPException(409, detail={"code": "message_media_limit_reached"})


async def list_participant_message_media(
    db: AsyncSession, message_id: uuid.UUID, user_id: uuid.UUID
) -> list[MessageMedia]:
    participant = await db.scalar(
        select(Message.id)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            Message.id == message_id,
            or_(Conversation.buyer_id == user_id, Conversation.seller_id == user_id),
        )
    )
    if participant is None:
        raise HTTPException(404, detail={"code": "message_not_found"})
    return list(
        (
            await db.scalars(
                select(MessageMedia)
                .where(MessageMedia.message_id == message_id)
                .order_by(MessageMedia.position)
            )
        ).all()
    )


async def participant_media(
    db: AsyncSession, media_id: uuid.UUID, user_id: uuid.UUID
) -> MessageMedia:
    media = await db.scalar(
        select(MessageMedia)
        .join(Message, Message.id == MessageMedia.message_id)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            MessageMedia.id == media_id,
            or_(Conversation.buyer_id == user_id, Conversation.seller_id == user_id),
        )
    )
    if media is None:
        raise HTTPException(404, detail={"code": "message_media_not_found"})
    return media


async def moderation_media(db: AsyncSession, media_id: uuid.UUID) -> MessageMedia:
    media = await db.get(MessageMedia, media_id)
    if media is None:
        raise HTTPException(404, detail={"code": "message_media_not_found"})
    return media
