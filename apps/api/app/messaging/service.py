import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import case, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models import Conversation, Listing, Message, Notification, User
from app.queueing.service import enqueue_notification_created


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
    if created_id:
        recipient_id = (
            conversation.seller_id if sender_id == conversation.buyer_id else conversation.buyer_id
        )
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


async def list_messages(
    db: AsyncSession, conversation_id: uuid.UUID, limit: int, offset: int
) -> list[Message]:
    return list((await db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc(), Message.id)
        .limit(limit)
        .offset(offset)
    )).all())


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
