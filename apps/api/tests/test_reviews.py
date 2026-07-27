import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.reviews.schemas import ReviewCreate
from app.reviews.service import create_review
from app.models import Conversation


@pytest.mark.parametrize("rating", [0, 6])
def test_review_rating_is_bounded(rating: int) -> None:
    with pytest.raises(ValidationError):
        ReviewCreate(rating=rating)


def test_review_comment_is_trimmed() -> None:
    review = ReviewCreate(rating=5, comment="  Отличная сделка  ")
    assert review.comment == "Отличная сделка"


@pytest.mark.asyncio
async def test_review_requires_two_sided_interaction() -> None:
    reviewer_id = uuid.uuid4()
    conversation = Conversation(
        id=uuid.uuid4(),
        listing_id=uuid.uuid4(),
        buyer_id=reviewer_id,
        seller_id=uuid.uuid4(),
    )
    db = AsyncMock()
    db.scalar.side_effect = [conversation, 1]

    with pytest.raises(HTTPException) as error:
        await create_review(db, conversation.id, reviewer_id, 5, "Хорошо")

    assert error.value.status_code == 409
    db.commit.assert_not_awaited()
