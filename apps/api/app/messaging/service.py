import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import case, delete, exists, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models import (
    Conversation,
    ConversationMute,
    Listing,
    Message,
    MessageMedia,
    Notification,
    User,
)
from app.queueing.service import enqueue_notification_created
from app.blocking.service import ensure_messaging_allowed


async def participant_conversation(
    db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID
) -> Conversation:
    conversation = await db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            or_(Conversation.buyer_id == user_id, Conversation.seller_id == user_id),
        )
    )
    if conversation is None:
        raise HTTPException(404, detail={"code": "conversation_not_found"})
    return conversation


async def create_conversation(
    db: AsyncSession, user_id: uuid.UUID, listing_id: uuid.UUID
) -> Conversation:
    listing = await db.scalar(
        select(Listing).where(Listing.id == listing_id, Listing.status == "active")
    )
    if listing is None:
        raise HTTPException(404, detail={"code": "listing_not_found"})
    if listing.owner_id == user_id:
        raise HTTPException(409, detail={"code": "cannot_message_self"})
    await ensure_messaging_allowed(db, user_id, listing.owner_id)

    conversation_id = uuid.uuid4()
    created_id = await db.scalar(
        insert(Conversation)
        .values(
            id=conversation_id,
            listing_id=listing.id,
            buyer_id=user_id,
            seller_id=listing.owner_id,
        )
        .on_conflict_do_nothing(index_elements=["listing_id", "buyer_id"])
        .returning(Conversation.id)
    )
    lookup = (
        Conversation.id == created_id
        if created_id
        else (
            (Conversation.listing_id == listing.id)
            & (Conversation.buyer_id == user_id)
        )
    )
    conversation = await db.scalar(select(Conversation).where(lookup))
    if conversation is None:
        raise RuntimeError("conversation upsert failed")
    if created_id:
        notification_id = uuid.uuid4()
        created_notification_id = await db.scalar(
            insert(Notification)
            .values(
                id=notification_id,
                user_id=listing.owner_id,
                kind="new_conversation",
                source_key=f"conversation:{conversation.id}",
                conversation_id=conversation.id,
            )
            .on_conflict_do_nothing(index_elements=["user_id", "source_key"])
            .returning(Notification.id)
        )
        if created_notification_id:
            await enqueue_notification_created(
                db,
                notification_id=created_notification_id,
                user_id=listing.owner_id,
                kind="new_conversation",
            )
    await db.commit()
    return conversation


async def send_message(
    db: AsyncSession,
    conversation: Conversation,
    sender_id: uuid.UUID,
    client_message_id: uuid.UUID,
    body: str,
) -> Message:
    recipient_id = (
        conversation.seller_id if sender_id == conversation.buyer_id else conversation.buyer_id
    )
    await ensure_messaging_allowed(db, sender_id, recipient_id)
    message_id = uuid.uuid4()
    created_id = await db.scalar(
        insert(Message)
        .values(
            id=message_id,
            conversation_id=conversation.id,
            sender_id=sender_id,
            client_message_id=client_message_id,
            body=body,
        )
        .on_conflict_do_nothing(index_elements=["sender_id", "client_message_id"])
        .returning(Message.id)
    )
    message = await db.scalar(
        select(Message).where(
            Message.id == created_id
            if created_id
            else (
                (Message.sender_id == sender_id)
                & (Message.client_message_id == client_message_id)
            )
        )
    )
    if message is None:
        raise RuntimeError("message upsert failed")
    if message.conversation_id != conversation.id:
        raise HTTPException(409, detail={"code": "client_message_id_reused"})
    if not created_id and message.body != body:
        raise HTTPException(409, detail={"code": "client_message_payload_changed"})
    recipient_muted = False
    if created_id:
        recipient_muted = bool(
            await db.scalar(
                select(
                    exists().where(
                        ConversationMute.user_id == recipient_id,
                        ConversationMute.conversation_id == conversation.id,
                    )
                )
            )
        )
    if created_id and not recipient_muted:
        notification_id = uuid.uuid4()
        created_notification_id = await db.scalar(
            insert(Notification)
            .values(
                id=notification_id,
                user_id=recipient_id,
                kind="new_message",
                source_key=f"message:{message.id}",
                conversation_id=conversation.id,
            )
            .on_conflict_do_nothing(index_elements=["user_id", "source_key"])
            .returning(Notification.id)
        )
        if created_notification_id:
            await enqueue_notification_created(
                db,
                notification_id=created_notification_id,
                user_id=recipient_id,
                kind="new_message",
            )
    if created_id:
        conversation.updated_at = datetime.now(UTC)
    await db.commit()
    return message


async def list_conversations(
    db: AsyncSession, user_id: uuid.UUID, limit: int, offset: int
) -> list[dict[str, object]]:
    buyer = aliased(User)
    seller = aliased(User)
    result = await db.execute(
        select(
            Conversation.id,
            Conversation.listing_id,
            Conversation.buyer_id,
            Conversation.seller_id,
            Conversation.created_at,
            Conversation.updated_at,
            Listing.title.label("listing_title"),
            case(
                (Conversation.buyer_id == user_id, Conversation.seller_id),
                else_=Conversation.buyer_id,
            ).label("counterpart_id"),
            case(
                (Conversation.buyer_id == user_id, seller.display_name),
                else_=buyer.display_name,
            ).label("counterpart_name"),
            exists()
            .where(
                ConversationMute.user_id == user_id,
                ConversationMute.conversation_id == Conversation.id,
            )
            .label("is_muted"),
        )
        .join(Listing, Listing.id == Conversation.listing_id)
        .join(buyer, buyer.id == Conversation.buyer_id)
        .join(seller, seller.id == Conversation.seller_id)
        .where(or_(Conversation.buyer_id == user_id, Conversation.seller_id == user_id))
        .order_by(Conversation.updated_at.desc(), Conversation.id)
        .limit(limit)
        .offset(offset)
    )
    return [dict(row) for row in result.mappings().all()]


async def mute_conversation(
    db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    await participant_conversation(db, conversation_id, user_id)
    await db.execute(
        insert(ConversationMute)
        .values(user_id=user_id, conversation_id=conversation_id)
        .on_conflict_do_nothing(index_elements=["user_id", "conversation_id"])
    )
    await db.commit()


async def unmute_conversation(
    db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    await participant_conversation(db, conversation_id, user_id)
    await db.execute(
        delete(ConversationMute).where(
            ConversationMute.user_id == user_id,
            ConversationMute.conversation_id == conversation_id,
        )
    )
    await db.commit()


async def list_messages(
    db: AsyncSession, conversation_id: uuid.UUID, limit: int, offset: int
) -> list[dict[str, object]]:
    messages = list(
        (
            await db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc(), Message.id)
                .limit(limit)
                .offset(offset)
            )
        ).all()
    )
    if not messages:
        return []
    media = list(
        (
            await db.scalars(
                select(MessageMedia)
                .where(MessageMedia.message_id.in_([message.id for message in messages]))
                .order_by(MessageMedia.message_id, MessageMedia.position)
            )
        ).all()
    )
    media_by_message: dict[uuid.UUID, list[MessageMedia]] = {}
    for item in media:
        media_by_message.setdefault(item.message_id, []).append(item)
    return [
        {
            **{column.name: getattr(message, column.name) for column in Message.__table__.columns},
            "media": media_by_message.get(message.id, []),
        }
        for message in messages
    ]


async def mark_conversation_read(
    db: AsyncSession,
    conversation: Conversation,
    user_id: uuid.UUID,
) -> dict[str, object]:
    read_at = datetime.now(UTC)
    unread_ids = list(
        (
            await db.scalars(
                update(Message)
                .where(
                    Message.conversation_id == conversation.id,
                    Message.sender_id != user_id,
                    Message.read_at.is_(None),
                )
                .values(
                    read_at=read_at,
                    delivered_at=func.coalesce(Message.delivered_at, read_at),
                )
                .returning(Message.id)
            )
        ).all()
    )
    if not unread_ids:
        await db.rollback()
        return {"read_count": 0, "read_at": None}
    await db.commit()
    return {"read_count": len(unread_ids), "read_at": read_at}


async def mark_conversation_delivered(
    db: AsyncSession,
    conversation: Conversation,
    user_id: uuid.UUID,
) -> dict[str, object]:
    delivered_at = datetime.now(UTC)
    delivered_ids = list(
        (
            await db.scalars(
                update(Message)
                .where(
                    Message.conversation_id == conversation.id,
                    Message.sender_id != user_id,
                    Message.delivered_at.is_(None),
                )
                .values(delivered_at=delivered_at)
                .returning(Message.id)
            )
        ).all()
    )
    if not delivered_ids:
        await db.rollback()
        return {"delivered_count": 0, "delivered_at": None}
    await db.commit()
    return {"delivered_count": len(delivered_ids), "delivered_at": delivered_at}


async def list_notifications(
    db: AsyncSession, user_id: uuid.UUID, limit: int, offset: int
) -> list[Notification]:
    return list((await db.scalars(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc(), Notification.id)
        .limit(limit)
        .offset(offset)
    )).all())


async def mark_notification_read(
    db: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID
) -> Notification:
    notification = await db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    if notification is None:
        raise HTTPException(404, detail={"code": "notification_not_found"})
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        await db.commit()
    return notification
