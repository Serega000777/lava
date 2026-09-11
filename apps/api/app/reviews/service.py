import uuid
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.messaging.service import participant_conversation
from app.models import (
    Interaction,
    Review,
    ReviewDispute,
    ReviewModerationDecision,
    ReviewReply,
    User,
)
from app.reviews.schemas import ReviewDisputeDecisionCreate


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
        .where(
            Review.reviewee_id == user_id,
            ~exists().where(
                ReviewDispute.review_id == Review.id,
                ReviewModerationDecision.dispute_id == ReviewDispute.id,
                ReviewModerationDecision.outcome == "exclude",
            ),
        )
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


async def received_reviews(
    db: AsyncSession, user_id: uuid.UUID, limit: int, offset: int
) -> list[dict[str, object]]:
    reviewer = aliased(User)
    responder = aliased(User)
    result = await db.execute(
        select(
            Review.id,
            reviewer.display_name.label("reviewer_name"),
            Review.rating,
            Review.comment,
            Review.created_at,
            ReviewReply.id.label("reply_id"),
            responder.display_name.label("responder_name"),
            ReviewReply.body.label("reply_body"),
            ReviewReply.created_at.label("reply_created_at"),
            ReviewDispute.id.label("dispute_id"),
            ReviewModerationDecision.outcome.label("dispute_outcome"),
            ReviewModerationDecision.reason_code.label("dispute_resolution_reason"),
            ReviewModerationDecision.comment.label("dispute_resolution_comment"),
        )
        .join(reviewer, reviewer.id == Review.reviewer_id)
        .outerjoin(ReviewReply, ReviewReply.review_id == Review.id)
        .outerjoin(responder, responder.id == ReviewReply.author_id)
        .outerjoin(ReviewDispute, ReviewDispute.review_id == Review.id)
        .outerjoin(
            ReviewModerationDecision,
            ReviewModerationDecision.dispute_id == ReviewDispute.id,
        )
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
        dispute_id = item.pop("dispute_id")
        dispute_outcome = item.pop("dispute_outcome")
        item["reply"] = (
            {
                "responder_name": responder_name,
                "body": reply_body,
                "created_at": reply_created_at,
            }
            if reply_id is not None
            else None
        )
        item["dispute_status"] = dispute_outcome or (
            "open" if dispute_id is not None else None
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


async def create_review_dispute(
    db: AsyncSession,
    review_id: uuid.UUID,
    opened_by: uuid.UUID,
    reason_code: str,
    details: str,
) -> ReviewDispute:
    review = await db.scalar(
        select(Review).where(Review.id == review_id, Review.reviewee_id == opened_by)
    )
    if review is None:
        raise HTTPException(404, detail={"code": "review_not_found"})
    dispute_id = await db.scalar(
        insert(ReviewDispute)
        .values(
            id=uuid.uuid4(),
            review_id=review.id,
            opened_by=opened_by,
            reason_code=reason_code,
            details=details,
        )
        .on_conflict_do_nothing(index_elements=["review_id"])
        .returning(ReviewDispute.id)
    )
    if dispute_id is None:
        raise HTTPException(409, detail={"code": "review_dispute_already_exists"})
    dispute = await db.scalar(select(ReviewDispute).where(ReviewDispute.id == dispute_id))
    if dispute is None:
        raise RuntimeError("review dispute insert failed")
    await db.commit()
    return dispute


async def list_review_disputes(
    db: AsyncSession, limit: int, offset: int
) -> list[dict[str, object]]:
    reviewer = aliased(User)
    reviewee = aliased(User)
    result = await db.execute(
        select(
            ReviewDispute.id,
            ReviewDispute.review_id,
            ReviewDispute.reason_code,
            ReviewDispute.details,
            ReviewDispute.created_at,
            Review.rating,
            Review.comment.label("review_comment"),
            reviewer.display_name.label("reviewer_name"),
            reviewee.display_name.label("reviewee_name"),
        )
        .join(Review, Review.id == ReviewDispute.review_id)
        .join(reviewer, reviewer.id == Review.reviewer_id)
        .join(reviewee, reviewee.id == Review.reviewee_id)
        .where(
            ~exists().where(
                ReviewModerationDecision.dispute_id == ReviewDispute.id
            )
        )
        .order_by(ReviewDispute.created_at, ReviewDispute.id)
        .limit(limit)
        .offset(offset)
    )
    return [dict(row) for row in result.mappings().all()]


async def decide_review_dispute(
    db: AsyncSession,
    dispute_id: uuid.UUID,
    moderator_id: uuid.UUID,
    data: ReviewDisputeDecisionCreate,
) -> ReviewModerationDecision:
    dispute = await db.scalar(
        select(ReviewDispute)
        .where(ReviewDispute.id == dispute_id)
        .with_for_update()
    )
    if dispute is None:
        raise HTTPException(404, detail={"code": "review_dispute_not_found"})
    review = await db.scalar(select(Review).where(Review.id == dispute.review_id))
    if review is None:
        raise RuntimeError("disputed review is missing")
    if moderator_id in {review.reviewer_id, review.reviewee_id}:
        raise HTTPException(409, detail={"code": "independent_review_required"})
    decision_id = await db.scalar(
        insert(ReviewModerationDecision)
        .values(
            id=uuid.uuid4(),
            dispute_id=dispute.id,
            moderator_id=moderator_id,
            outcome=data.outcome,
            reason_code=data.reason_code,
            comment=data.comment,
        )
        .on_conflict_do_nothing(index_elements=["dispute_id"])
        .returning(ReviewModerationDecision.id)
    )
    if decision_id is None:
        raise HTTPException(409, detail={"code": "review_dispute_already_decided"})
    decision = await db.scalar(
        select(ReviewModerationDecision).where(
            ReviewModerationDecision.id == decision_id
        )
    )
    if decision is None:
        raise RuntimeError("review moderation decision insert failed")
    await db.commit()
    return decision


async def reputation(db: AsyncSession, user_id: uuid.UUID) -> tuple[Decimal | None, int]:
    row = (
        await db.execute(
            select(func.avg(Review.rating), func.count(Review.id)).where(
                Review.reviewee_id == user_id,
                ~exists().where(
                    ReviewDispute.review_id == Review.id,
                    ReviewModerationDecision.dispute_id == ReviewDispute.id,
                    ReviewModerationDecision.outcome == "exclude",
                ),
            )
        )
    ).one()
    average = Decimal(row[0]).quantize(Decimal("0.01")) if row[0] is not None else None
    return average, int(row[1])
