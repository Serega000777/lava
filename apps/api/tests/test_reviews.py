import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.reviews.schemas import ReviewCreate
from app.reviews.service import create_review
from app.models import Conversation, Interaction, Review


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
    interaction = Interaction(id=uuid.uuid4(), conversation_id=conversation.id)
    db = AsyncMock()
    db.scalar.side_effect = [conversation, interaction]

    with pytest.raises(HTTPException) as error:
        await create_review(db, conversation.id, reviewer_id, 5, "Хорошо")

    assert error.value.status_code == 409
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_review_is_linked_to_confirmed_interaction() -> None:
    reviewer_id = uuid.uuid4()
    conversation = Conversation(
        id=uuid.uuid4(),
        listing_id=uuid.uuid4(),
        buyer_id=reviewer_id,
        seller_id=uuid.uuid4(),
    )
    completed_at = datetime.now(UTC)
    interaction = Interaction(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        contacted_at=completed_at,
        buyer_confirmed_at=completed_at,
        seller_confirmed_at=completed_at,
        completed_at=completed_at,
    )
    review_id = uuid.uuid4()
    created = Review(
        id=review_id,
        conversation_id=conversation.id,
        interaction_id=interaction.id,
        reviewer_id=reviewer_id,
        reviewee_id=conversation.seller_id,
        rating=5,
        comment="Хорошо",
    )
    db = AsyncMock()
    db.scalar.side_effect = [conversation, interaction, review_id, created]

    result = await create_review(db, conversation.id, reviewer_id, 5, "Хорошо")

    assert result is created
    insert_statement = db.scalar.await_args_list[2].args[0]
    assert insert_statement.compile().params["interaction_id"] == interaction.id
    db.commit.assert_awaited_once()
