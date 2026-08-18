import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import current_user, get_db
from app.messaging.schemas import (
    ConversationCreate,
    ConversationResponse,
    ConversationSummary,
    DeliveryReceiptResponse,
    MessageCreate,
    MessageResponse,
    NotificationResponse,
    ReadReceiptResponse,
)
from app.messaging.abuse import message_rate_limited
from app.config import settings
from app.blocking.service import ensure_messaging_allowed
from app.messaging.service import (
    create_conversation,
    list_conversations,
    list_messages,
    list_notifications,
    mark_notification_read,
    mark_conversation_read,
    mark_conversation_delivered,
    mute_conversation,
    participant_conversation,
    send_message,
    unmute_conversation,
)
from app.models import User

router = APIRouter(tags=["messaging"])


@router.post("/conversations", response_model=ConversationResponse)
async def start_conversation(
    data: ConversationCreate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_conversation(db, user.id, data.listing_id)


@router.get("/conversations", response_model=list[ConversationSummary])
async def conversations(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_conversations(db, user.id, limit, offset)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def messages(
    conversation_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await participant_conversation(db, conversation_id, user.id)
    return await list_messages(db, conversation.id, limit, offset)


@router.patch(
    "/conversations/{conversation_id}/read", response_model=ReadReceiptResponse
)
async def read_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    conversation = await participant_conversation(db, conversation_id, user.id)
    return await mark_conversation_read(db, conversation, user.id)


@router.patch(
    "/conversations/{conversation_id}/delivered",
    response_model=DeliveryReceiptResponse,
)
async def deliver_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    conversation = await participant_conversation(db, conversation_id, user.id)
    return await mark_conversation_delivered(db, conversation, user.id)


@router.put("/conversations/{conversation_id}/mute", status_code=204)
async def mute(
    conversation_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await mute_conversation(db, conversation_id, user.id)


@router.delete("/conversations/{conversation_id}/mute", status_code=204)
async def unmute(
    conversation_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await unmute_conversation(db, conversation_id, user.id)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=201,
)
async def create_message(
    conversation_id: uuid.UUID,
    data: MessageCreate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await participant_conversation(db, conversation_id, user.id)
    recipient_id = (
        conversation.seller_id
        if user.id == conversation.buyer_id
        else conversation.buyer_id
    )
    await ensure_messaging_allowed(db, user.id, recipient_id)
    redis = Redis.from_url(settings.redis_url)
    try:
        limited = await message_rate_limited(
            redis, user.id, conversation.id, data.client_message_id
        )
    except RedisError as error:
        raise HTTPException(
            503, detail={"code": "security_dependency_unavailable"}
        ) from error
    finally:
        await redis.aclose()
    if limited:
        raise HTTPException(
            429,
            detail={"code": "message_rate_limited"},
            headers={"Retry-After": str(settings.message_rate_window_seconds)},
        )
    return await send_message(
        db, conversation, user.id, data.client_message_id, data.body
    )


@router.get("/notifications", response_model=list[NotificationResponse])
async def notifications(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_notifications(db, user.id, limit, offset)


@router.patch("/notifications/{notification_id}/read", response_model=NotificationResponse)
async def read_notification(
    notification_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    return await mark_notification_read(db, notification_id, user.id)
