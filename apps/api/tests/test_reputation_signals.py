import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.reviews.signals import (
    ReputationSignalInput,
    assess_reputation_activity,
    list_reputation_signals,
)


def review_input(
    reviewer_id: uuid.UUID,
    rating: int,
    *,
    created_at: datetime,
) -> ReputationSignalInput:
    return ReputationSignalInput(
        reviewer_id=reviewer_id,
        rating=rating,
        reviewer_created_at=created_at,
    )


def test_signal_requires_multiple_explainable_indicators() -> None:
    now = datetime(2026, 9, 3, tzinfo=UTC)
    reviews = [
        review_input(uuid.uuid4(), 5, created_at=now - timedelta(days=1))
        for _ in range(3)
    ]

    signal = assess_reputation_activity(reviews, now=now)

    assert signal["detected"] is True
    assert signal["indicators"] == ["new_account_cluster", "rating_concentration"]
    assert signal["distinct_reviewer_count"] == 3
    assert signal["dominant_rating"] == 5


def test_single_weak_indicator_does_not_raise_signal() -> None:
    now = datetime(2026, 9, 3, tzinfo=UTC)
    ratings = [1, 2, 3, 4, 5]
    reviews = [
        review_input(
            uuid.uuid4(),
            rating,
            created_at=now - timedelta(days=90),
        )
        for rating in ratings
    ]

    signal = assess_reputation_activity(reviews, now=now)

    assert signal["detected"] is False
    assert signal["indicators"] == ["review_burst"]


def test_repeat_relationships_are_counted_without_exposing_reviewers() -> None:
    now = datetime(2026, 9, 3, tzinfo=UTC)
    first_reviewer = uuid.uuid4()
    second_reviewer = uuid.uuid4()
    reviews = [
        review_input(first_reviewer, 5, created_at=now - timedelta(days=30)),
        review_input(first_reviewer, 5, created_at=now - timedelta(days=30)),
        review_input(first_reviewer, 5, created_at=now - timedelta(days=30)),
        review_input(second_reviewer, 5, created_at=now - timedelta(days=30)),
        review_input(second_reviewer, 5, created_at=now - timedelta(days=30)),
    ]

    signal = assess_reputation_activity(reviews, now=now)

    assert signal["detected"] is True
    assert signal["repeat_review_count"] == 3
    assert "repeat_reviewer_relationships" in signal["indicators"]
    assert "reviewer_ids" not in signal


@pytest.mark.asyncio
async def test_list_signals_skips_detail_query_without_candidates() -> None:
    db = MagicMock()
    db.scalars = AsyncMock()
    db.execute = AsyncMock()
    scalar_result = MagicMock()
    scalar_result.all.return_value = []
    db.scalars.return_value = scalar_result

    assert await list_reputation_signals(db, limit=50, offset=0) == []
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_signals_returns_privacy_safe_moderator_summary() -> None:
    db = MagicMock()
    db.scalars = AsyncMock()
    db.execute = AsyncMock()
    subject_id = uuid.uuid4()
    candidate_result = MagicMock()
    candidate_result.all.return_value = [subject_id]
    db.scalars.return_value = candidate_result

    now = datetime.now(UTC)
    detail_result = MagicMock()
    detail_result.all.return_value = [
        (subject_id, "Магазин", uuid.uuid4(), 5, now - timedelta(days=1))
        for _ in range(3)
    ]
    db.execute.return_value = detail_result

    signals = await list_reputation_signals(db, limit=50, offset=0)

    assert signals == [
        {
            "user_id": subject_id,
            "display_name": "Магазин",
            "detected": True,
            "window_hours": 24,
            "review_count": 3,
            "distinct_reviewer_count": 3,
            "new_account_reviewer_count": 3,
            "dominant_rating": 5,
            "dominant_rating_count": 3,
            "repeat_review_count": 0,
            "indicators": ["new_account_cluster", "rating_concentration"],
        }
    ]
    assert "reviewer_id" not in signals[0]
