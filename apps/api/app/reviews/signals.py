import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models import Review, ReviewDispute, ReviewModerationDecision, User

SIGNAL_WINDOW_HOURS = 24
NEW_ACCOUNT_MAX_AGE_DAYS = 7
MIN_REVIEWS_FOR_ANALYSIS = 3
REVIEW_BURST_THRESHOLD = 5
RATING_CONCENTRATION_RATIO = 0.9
MAX_SIGNAL_CANDIDATES = 1_000


@dataclass(frozen=True)
class ReputationSignalInput:
    reviewer_id: uuid.UUID
    rating: int
    reviewer_created_at: datetime


def assess_reputation_activity(
    reviews: list[ReputationSignalInput], *, now: datetime
) -> dict[str, object]:
    """Build an explainable advisory signal without device or network identifiers."""
    review_count = len(reviews)
    distinct_reviewer_count = len({review.reviewer_id for review in reviews})
    new_account_cutoff = now - timedelta(days=NEW_ACCOUNT_MAX_AGE_DAYS)
    new_account_reviewer_count = len(
        {
            review.reviewer_id
            for review in reviews
            if review.reviewer_created_at >= new_account_cutoff
        }
    )
    rating_counts = Counter(review.rating for review in reviews)
    dominant_rating, dominant_rating_count = (
        rating_counts.most_common(1)[0] if rating_counts else (None, 0)
    )
    repeat_review_count = review_count - distinct_reviewer_count

    indicators: list[str] = []
    if review_count >= REVIEW_BURST_THRESHOLD:
        indicators.append("review_burst")
    if new_account_reviewer_count >= MIN_REVIEWS_FOR_ANALYSIS:
        indicators.append("new_account_cluster")
    if (
        review_count >= MIN_REVIEWS_FOR_ANALYSIS
        and dominant_rating_count / review_count >= RATING_CONCENTRATION_RATIO
    ):
        indicators.append("rating_concentration")
    if repeat_review_count >= 2:
        indicators.append("repeat_reviewer_relationships")

    return {
        "detected": len(indicators) >= 2,
        "window_hours": SIGNAL_WINDOW_HOURS,
        "review_count": review_count,
        "distinct_reviewer_count": distinct_reviewer_count,
        "new_account_reviewer_count": new_account_reviewer_count,
        "dominant_rating": dominant_rating,
        "dominant_rating_count": dominant_rating_count,
        "repeat_review_count": repeat_review_count,
        "indicators": indicators,
    }


def _not_moderator_excluded():
    return ~exists().where(
        ReviewDispute.review_id == Review.id,
        ReviewModerationDecision.dispute_id == ReviewDispute.id,
        ReviewModerationDecision.outcome == "exclude",
    )


async def list_reputation_signals(
    db: AsyncSession, *, limit: int, offset: int
) -> list[dict[str, object]]:
    now = datetime.now(UTC)
    window_start = now - timedelta(hours=SIGNAL_WINDOW_HOURS)
    candidate_ids = list(
        (
            await db.scalars(
                select(Review.reviewee_id)
                .where(
                    Review.created_at >= window_start,
                    _not_moderator_excluded(),
                )
                .group_by(Review.reviewee_id)
                .having(func.count(Review.id) >= MIN_REVIEWS_FOR_ANALYSIS)
                .order_by(func.count(Review.id).desc(), Review.reviewee_id)
                .limit(MAX_SIGNAL_CANDIDATES)
            )
        ).all()
    )
    if not candidate_ids:
        return []

    reviewer = aliased(User)
    reviewee = aliased(User)
    rows = (
        await db.execute(
            select(
                Review.reviewee_id,
                reviewee.display_name,
                Review.reviewer_id,
                Review.rating,
                reviewer.created_at,
            )
            .join(reviewee, reviewee.id == Review.reviewee_id)
            .join(reviewer, reviewer.id == Review.reviewer_id)
            .where(
                Review.reviewee_id.in_(candidate_ids),
                Review.created_at >= window_start,
                _not_moderator_excluded(),
            )
            .order_by(Review.reviewee_id, Review.created_at)
        )
    ).all()

    grouped: dict[uuid.UUID, tuple[str, list[ReputationSignalInput]]] = {}
    for reviewee_id, display_name, reviewer_id, rating, reviewer_created_at in rows:
        _, inputs = grouped.setdefault(reviewee_id, (display_name, []))
        inputs.append(
            ReputationSignalInput(
                reviewer_id=reviewer_id,
                rating=rating,
                reviewer_created_at=reviewer_created_at,
            )
        )

    results: list[dict[str, object]] = []
    for user_id in candidate_ids:
        grouped_item = grouped.get(user_id)
        if grouped_item is None:
            continue
        display_name, inputs = grouped_item
        signal = assess_reputation_activity(inputs, now=now)
        if signal["detected"]:
            results.append(
                {
                    "user_id": user_id,
                    "display_name": display_name,
                    **signal,
                }
            )

    return results[offset : offset + limit]
