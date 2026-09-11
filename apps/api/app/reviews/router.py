import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import current_user, get_db, require_permission
from app.models import User
from app.reviews.schemas import (
    ModerationReviewDisputeResponse,
    PublicReviewResponse,
    ReceivedReviewResponse,
    ReputationResponse,
    ReputationSignalResponse,
    ReviewCreate,
    ReviewReplyCreate,
    ReviewReplyResponse,
    ReviewResponse,
    ReviewDisputeCreate,
    ReviewDisputeDecisionCreate,
    ReviewDisputeDecisionResponse,
    ReviewDisputeResponse,
)
from app.reviews.signals import list_reputation_signals
from app.reviews.service import (
    create_review,
    create_review_reply,
    create_review_dispute,
    decide_review_dispute,
    ensure_user_exists,
    public_reviews,
    received_reviews,
    reputation,
    list_review_disputes,
)

router = APIRouter(tags=["reviews"])


@router.get(
    "/moderation/reputation-signals",
    response_model=list[ReputationSignalResponse],
)
async def moderation_reputation_signals(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=999),
    _: User = Depends(require_permission("moderation:read")),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, object]]:
    return await list_reputation_signals(db, limit=limit, offset=offset)


@router.get("/reviews/received", response_model=list[ReceivedReviewResponse])
async def my_received_reviews(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, object]]:
    return await received_reviews(db, user.id, limit, offset)


@router.post(
    "/reviews/{review_id}/dispute",
    response_model=ReviewDisputeResponse,
    status_code=201,
)
async def dispute_review(
    review_id: uuid.UUID,
    data: ReviewDisputeCreate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewDisputeResponse:
    return ReviewDisputeResponse.model_validate(
        await create_review_dispute(
            db, review_id, user.id, data.reason_code, data.details
        )
    )


@router.get(
    "/moderation/review-disputes",
    response_model=list[ModerationReviewDisputeResponse],
)
async def moderation_review_disputes(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
    _: User = Depends(require_permission("moderation:read")),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, object]]:
    return await list_review_disputes(db, limit, offset)


@router.post(
    "/moderation/review-disputes/{dispute_id}/decision",
    response_model=ReviewDisputeDecisionResponse,
    status_code=201,
)
async def review_dispute_decision(
    dispute_id: uuid.UUID,
    data: ReviewDisputeDecisionCreate,
    user: User = Depends(require_permission("moderation:decide")),
    db: AsyncSession = Depends(get_db),
) -> ReviewDisputeDecisionResponse:
    return ReviewDisputeDecisionResponse.model_validate(
        await decide_review_dispute(db, dispute_id, user.id, data)
    )


@router.post(
    "/reviews/{review_id}/reply",
    response_model=ReviewReplyResponse,
    status_code=201,
)
async def reply_to_review(
    review_id: uuid.UUID,
    data: ReviewReplyCreate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewReplyResponse:
    return ReviewReplyResponse.model_validate(
        await create_review_reply(db, review_id, user.id, data.body)
    )


@router.post(
    "/conversations/{conversation_id}/review",
    response_model=ReviewResponse,
    status_code=201,
)
async def review_conversation(
    conversation_id: uuid.UUID,
    data: ReviewCreate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    review = await create_review(
        db, conversation_id, user.id, data.rating, data.comment
    )
    return ReviewResponse(
        id=review.id,
        conversation_id=review.conversation_id,
        reviewer_id=review.reviewer_id,
        reviewee_id=review.reviewee_id,
        reviewer_name=user.display_name,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
    )


@router.get("/users/{user_id}/reviews", response_model=list[PublicReviewResponse])
async def user_reviews(
    user_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
    db: AsyncSession = Depends(get_db),
):
    await ensure_user_exists(db, user_id)
    return await public_reviews(db, user_id, limit, offset)


@router.get("/users/{user_id}/reputation", response_model=ReputationResponse)
async def user_reputation(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ReputationResponse:
    await ensure_user_exists(db, user_id)
    average, count = await reputation(db, user_id)
    return ReputationResponse(user_id=user_id, average_rating=average, review_count=count)
