import uuid
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.messaging.service import participant_conversation
from app.models import Interaction, Review, ReviewReply, User


async def ensure_user_exists(db: AsyncSession, user_id: uuid.UUID) -> None:
    if await db.scalar(select(User.id).where(User.id == user_id)) is None:
        raise HTTPException(404, detail={"code": "user_not_found"})


async def create_review(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    reviewer_id: uuid.UUID,
    rating: int,
    comment: str,
) -> Review:
    conversation = await participant_conversation(db, conversation_id, reviewer_id)
    interaction = await db.scalar(
        select(Interaction).where(Interaction.conversation_id == conversation.id)
    )
    if interaction is None or interaction.completed_at is None:
        raise HTTPException(409, detail={"code": "interaction_not_completed"})

    reviewee_id = (
        conversation.seller_id
        if reviewer_id == conversation.buyer_id
        else conversation.buyer_id
    )
    review_id = await db.scalar(
        insert(Review)
        .values(
            id=uuid.uuid4(),
            conversation_id=conversation.id,
            interaction_id=interaction.id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            rating=rating,
            comment=comment,
        )
        .on_conflict_do_nothing(index_elements=["conversation_id", "reviewer_id"])
        .returning(Review.id)
    )
    if review_id is None:
        raise HTTPException(409, detail={"code": "review_already_exists"})
    review = await db.scalar(select(Review).where(Review.id == review_id))
    if review is None:
        raise RuntimeError("review insert failed")
    await db.commit()
    return review


async def public_reviews(
    db: AsyncSession, user_id: uuid.UUID, limit: int, offset: int
) -> list[dict[str, object]]:
    reviewer = aliased(User)
    responder = aliased(User)
    result = await db.execute(
        select(
            Review.id,
            Review.conversation_id,
            Review.reviewer_id,
            Review.reviewee_id,
            reviewer.display_name.label("reviewer_name"),
            Review.rating,
            Review.comment,
            Review.created_at,
            ReviewReply.id.label("reply_id"),
            responder.display_name.label("responder_name"),
            ReviewReply.body.label("reply_body"),
            ReviewReply.created_at.label("reply_created_at"),
        )
        .join(reviewer, reviewer.id == Review.reviewer_id)
        .outerjoin(ReviewReply, ReviewReply.review_id == Review.id)
        .outerjoin(responder, responder.id == ReviewReply.author_id)
        .where(Review.reviewee_id == user_id)
        .order_by(Review.created_at.desc(), Review.id)
        .limit(limit)
        .offset(offset)
    )
    reviews = []
    for row in result.mappings().all():
        item = dict(row)
        reply_id = item.pop("reply_id")
        responder_name = item.pop("responder_name")
        reply_body = item.pop("reply_body")
        reply_created_at = item.pop("reply_created_at")
        item["reply"] = (
            {
                "responder_name": responder_name,
                "body": reply_body,
                "created_at": reply_created_at,
            }
            if reply_id is not None
            else None
        )
        reviews.append(item)
    return reviews


async def create_review_reply(
    db: AsyncSession, review_id: uuid.UUID, author_id: uuid.UUID, body: str
) -> ReviewReply:
    review = await db.scalar(
        select(Review).where(Review.id == review_id, Review.reviewee_id == author_id)
    )
    if review is None:
        raise HTTPException(404, detail={"code": "review_not_found"})
    reply_id = await db.scalar(
        insert(ReviewReply)
        .values(
            id=uuid.uuid4(),
            review_id=review.id,
            author_id=author_id,
            body=body,
        )
        .on_conflict_do_nothing(index_elements=["review_id"])
        .returning(ReviewReply.id)
    )
    if reply_id is None:
        raise HTTPException(409, detail={"code": "review_reply_already_exists"})
    reply = await db.scalar(select(ReviewReply).where(ReviewReply.id == reply_id))
    if reply is None:
        raise RuntimeError("review reply insert failed")
    await db.commit()
    return reply


async def reputation(db: AsyncSession, user_id: uuid.UUID) -> tuple[Decimal | None, int]:
    row = (
        await db.execute(
            select(func.avg(Review.rating), func.count(Review.id)).where(
                Review.reviewee_id == user_id
            )
        )
    ).one()
    average = Decimal(row[0]).quantize(Decimal("0.01")) if row[0] is not None else None
    return average, int(row[1])
