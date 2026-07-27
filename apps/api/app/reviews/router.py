import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import current_user, get_db
from app.models import User
from app.reviews.schemas import (
    PublicReviewResponse,
    ReputationResponse,
    ReviewCreate,
    ReviewResponse,
)
from app.reviews.service import create_review, ensure_user_exists, public_reviews, reputation

router = APIRouter(tags=["reviews"])


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
