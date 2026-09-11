import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AiGeneration,
    Conversation,
    Favorite,
    Listing,
    Message,
    ModerationCase,
    OutboxTask,
    Review,
    User,
)


async def seller_metrics(
    db: AsyncSession, user_id: uuid.UUID, limit: int, offset: int
) -> list[dict[str, object]]:
    favorite_count = (
        select(func.count(Favorite.listing_id))
        .where(Favorite.listing_id == Listing.id)
        .correlate(Listing)
        .scalar_subquery()
    )
    conversation_count = (
        select(func.count(Conversation.id))
        .where(Conversation.listing_id == Listing.id)
        .correlate(Listing)
        .scalar_subquery()
    )
    message_count = (
        select(func.count(Message.id))
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Conversation.listing_id == Listing.id)
        .correlate(Listing)
        .scalar_subquery()
    )
    review_count = (
        select(func.count(Review.id))
        .join(Conversation, Conversation.id == Review.conversation_id)
        .where(Conversation.listing_id == Listing.id)
        .correlate(Listing)
        .scalar_subquery()
    )
    result = await db.execute(
        select(
            Listing.id.label("listing_id"),
            Listing.title,
            Listing.status,
            favorite_count.label("favorites"),
            conversation_count.label("conversations"),
            message_count.label("messages"),
            review_count.label("reviews"),
        )
        .where(Listing.owner_id == user_id)
        .order_by(Listing.updated_at.desc(), Listing.id)
        .limit(limit)
        .offset(offset)
    )
    return [dict(row) for row in result.mappings().all()]


async def admin_metrics(db: AsyncSession) -> dict[str, int]:
    row = (
        await db.execute(
            select(
                select(func.count(User.id)).scalar_subquery().label("users"),
                select(func.count(Listing.id))
                .where(Listing.status == "active")
                .scalar_subquery()
                .label("active_listings"),
                select(func.count(ModerationCase.id))
                .where(ModerationCase.status == "open")
                .scalar_subquery()
                .label("open_moderation_cases"),
                select(func.count(Conversation.id)).scalar_subquery().label("conversations"),
                select(func.count(Message.id)).scalar_subquery().label("messages"),
                select(func.count(Review.id)).scalar_subquery().label("reviews"),
                select(func.count(AiGeneration.id)).scalar_subquery().label("ai_generations"),
            )
        )
    ).mappings().one()
    return {key: int(value) for key, value in row.items()}


async def queue_metrics(
    db: AsyncSession, heartbeat_timestamp: int | None
) -> dict[str, int | bool | None]:
    row = (
        await db.execute(
            select(
                *[
                    select(func.count(OutboxTask.id))
                    .where(OutboxTask.status == status)
                    .scalar_subquery()
                    .label(status)
                    for status in ("pending", "processing", "failed", "completed")
                ],
                select(func.min(OutboxTask.created_at))
                .where(OutboxTask.status == "pending")
                .scalar_subquery()
                .label("oldest_pending_at"),
            )
        )
    ).mappings().one()
    now = datetime.now(UTC)
    oldest = row["oldest_pending_at"]
    heartbeat_age = max(0, int(now.timestamp()) - heartbeat_timestamp) if heartbeat_timestamp else None
    return {
        "pending": int(row["pending"]),
        "processing": int(row["processing"]),
        "failed": int(row["failed"]),
        "completed": int(row["completed"]),
        "oldest_pending_seconds": max(0, int((now - oldest).total_seconds())) if oldest else None,
        "worker_healthy": heartbeat_age is not None and heartbeat_age <= 30,
        "heartbeat_age_seconds": heartbeat_age,
    }
