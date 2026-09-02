import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.reviews.schemas import ReviewCreate, ReviewReplyCreate
from app.reviews.service import create_review, create_review_reply, public_reviews
from app.models import Conversation, Interaction, Review, ReviewReply


@pytest.mark.parametrize("rating", [0, 6])
def test_review_rating_is_bounded(rating: int) -> None:
    with pytest.raises(ValidationError):
        ReviewCreate(rating=rating)


def test_review_comment_is_trimmed() -> None:
    review = ReviewCreate(rating=5, comment="  Отличная сделка  ")
    assert review.comment == "Отличная сделка"


def test_review_reply_is_trimmed_and_rejects_blank_body() -> None:
    assert ReviewReplyCreate(body="  Спасибо  ").body == "Спасибо"
    with pytest.raises(ValidationError):
        ReviewReplyCreate(body="   ")


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


@pytest.mark.asyncio
async def test_only_reviewee_can_reply_without_exposing_foreign_review() -> None:
    db = AsyncMock()
    db.scalar.return_value = None

    with pytest.raises(HTTPException) as error:
        await create_review_reply(db, uuid.uuid4(), uuid.uuid4(), "Ответ")

    assert error.value.status_code == 404
    assert error.value.detail == {"code": "review_not_found"}
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_reviewee_reply_is_immutable_and_single() -> None:
    reviewee_id = uuid.uuid4()
    review = Review(
        id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        interaction_id=uuid.uuid4(),
        reviewer_id=uuid.uuid4(),
        reviewee_id=reviewee_id,
        rating=5,
        comment="Отлично",
    )
    reply_id = uuid.uuid4()
    reply = ReviewReply(
        id=reply_id,
        review_id=review.id,
        author_id=reviewee_id,
        body="Спасибо",
    )
    db = AsyncMock()
    db.scalar.side_effect = [review, reply_id, reply]

    result = await create_review_reply(db, review.id, reviewee_id, "Спасибо")

    assert result is reply
    db.commit.assert_awaited_once()

    duplicate_db = AsyncMock()
    duplicate_db.scalar.side_effect = [review, None]
    with pytest.raises(HTTPException) as error:
        await create_review_reply(duplicate_db, review.id, reviewee_id, "Ещё ответ")
    assert error.value.status_code == 409
    duplicate_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_public_reviews_nest_reply_without_private_ids() -> None:
    review_id = uuid.uuid4()
    result = MagicMock()
    result.mappings.return_value.all.return_value = [{
        "id": review_id,
        "conversation_id": uuid.uuid4(),
        "reviewer_id": uuid.uuid4(),
        "reviewee_id": uuid.uuid4(),
        "reviewer_name": "Покупатель",
        "rating": 5,
        "comment": "Всё хорошо",
        "created_at": datetime.now(UTC),
        "reply_id": uuid.uuid4(),
        "responder_name": "Продавец",
        "reply_body": "Спасибо",
        "reply_created_at": datetime.now(UTC),
    }]
    db = AsyncMock()
    db.execute.return_value = result

    reviews = await public_reviews(db, uuid.uuid4(), 50, 0)

    assert reviews[0]["reply"] == {
        "responder_name": "Продавец",
        "body": "Спасибо",
        "created_at": reviews[0]["reply"]["created_at"],
    }
    assert "reply_id" not in reviews[0]
