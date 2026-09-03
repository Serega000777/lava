import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.reviews.schemas import (
    ReviewCreate,
    ReviewDisputeDecisionCreate,
    ReviewReplyCreate,
)
from app.reviews.service import (
    create_review,
    create_review_dispute,
    create_review_reply,
    decide_review_dispute,
    public_reviews,
    received_reviews,
    reputation,
)
from app.models import (
    Conversation,
    Interaction,
    Review,
    ReviewDispute,
    ReviewModerationDecision,
    ReviewReply,
)


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


def test_review_dispute_decision_reason_matches_outcome() -> None:
    with pytest.raises(ValidationError):
        ReviewDisputeDecisionCreate(
            outcome="keep", reason_code="abusive", comment=""
        )
    with pytest.raises(ValidationError):
        ReviewDisputeDecisionCreate(
            outcome="exclude", reason_code="complies", comment=""
        )


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


@pytest.mark.asyncio
async def test_received_reviews_include_resolution_without_moderator_identity() -> None:
    result = MagicMock()
    result.mappings.return_value.all.return_value = [{
        "id": uuid.uuid4(),
        "reviewer_name": "Покупатель",
        "rating": 1,
        "comment": "Спорный отзыв",
        "created_at": datetime.now(UTC),
        "reply_id": None,
        "responder_name": None,
        "reply_body": None,
        "reply_created_at": None,
        "dispute_id": uuid.uuid4(),
        "dispute_outcome": "exclude",
        "dispute_resolution_reason": "abusive",
        "dispute_resolution_comment": "Нарушение подтверждено",
    }]
    db = AsyncMock()
    db.execute.return_value = result

    reviews = await received_reviews(db, uuid.uuid4(), 50, 0)

    assert reviews[0]["dispute_status"] == "exclude"
    assert reviews[0]["dispute_resolution_reason"] == "abusive"
    assert "moderator_id" not in reviews[0]


@pytest.mark.asyncio
async def test_only_reviewee_can_open_one_dispute() -> None:
    reviewee_id = uuid.uuid4()
    review = Review(
        id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        interaction_id=uuid.uuid4(),
        reviewer_id=uuid.uuid4(),
        reviewee_id=reviewee_id,
        rating=2,
        comment="Спорный отзыв",
    )
    dispute_id = uuid.uuid4()
    dispute = ReviewDispute(
        id=dispute_id,
        review_id=review.id,
        opened_by=reviewee_id,
        reason_code="abusive",
        details="Есть оскорбление",
    )
    db = AsyncMock()
    db.scalar.side_effect = [review, dispute_id, dispute]

    result = await create_review_dispute(
        db, review.id, reviewee_id, "abusive", "Есть оскорбление"
    )

    assert result is dispute
    db.commit.assert_awaited_once()

    foreign_db = AsyncMock()
    foreign_db.scalar.return_value = None
    with pytest.raises(HTTPException) as foreign_error:
        await create_review_dispute(
            foreign_db, review.id, uuid.uuid4(), "other", ""
        )
    assert foreign_error.value.status_code == 404

    duplicate_db = AsyncMock()
    duplicate_db.scalar.side_effect = [review, None]
    with pytest.raises(HTTPException) as duplicate_error:
        await create_review_dispute(
            duplicate_db, review.id, reviewee_id, "other", ""
        )
    assert duplicate_error.value.status_code == 409


@pytest.mark.asyncio
async def test_review_participant_cannot_moderate_own_dispute() -> None:
    review = Review(
        id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        interaction_id=uuid.uuid4(),
        reviewer_id=uuid.uuid4(),
        reviewee_id=uuid.uuid4(),
        rating=1,
        comment="Спор",
    )
    dispute = ReviewDispute(
        id=uuid.uuid4(),
        review_id=review.id,
        opened_by=review.reviewee_id,
        reason_code="other",
        details="",
    )
    db = AsyncMock()
    db.scalar.side_effect = [dispute, review]
    data = ReviewDisputeDecisionCreate(
        outcome="keep", reason_code="complies", comment=""
    )

    with pytest.raises(HTTPException) as error:
        await decide_review_dispute(db, dispute.id, review.reviewer_id, data)

    assert error.value.status_code == 409
    assert error.value.detail == {"code": "independent_review_required"}
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_independent_moderator_can_exclude_review_once() -> None:
    review = Review(
        id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        interaction_id=uuid.uuid4(),
        reviewer_id=uuid.uuid4(),
        reviewee_id=uuid.uuid4(),
        rating=1,
        comment="Персональные данные",
    )
    dispute = ReviewDispute(
        id=uuid.uuid4(),
        review_id=review.id,
        opened_by=review.reviewee_id,
        reason_code="personal_data",
        details="",
    )
    moderator_id = uuid.uuid4()
    decision_id = uuid.uuid4()
    data = ReviewDisputeDecisionCreate(
        outcome="exclude", reason_code="personal_data", comment="Подтверждено"
    )
    decision = ReviewModerationDecision(
        id=decision_id,
        dispute_id=dispute.id,
        moderator_id=moderator_id,
        outcome=data.outcome,
        reason_code=data.reason_code,
        comment=data.comment,
    )
    db = AsyncMock()
    db.scalar.side_effect = [dispute, review, decision_id, decision]

    result = await decide_review_dispute(db, dispute.id, moderator_id, data)

    assert result is decision
    db.commit.assert_awaited_once()

    duplicate_db = AsyncMock()
    duplicate_db.scalar.side_effect = [dispute, review, None]
    with pytest.raises(HTTPException) as error:
        await decide_review_dispute(duplicate_db, dispute.id, moderator_id, data)
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_reputation_excludes_only_moderator_excluded_reviews() -> None:
    query_result = MagicMock()
    query_result.one.return_value = (None, 0)
    db = AsyncMock()
    db.execute.return_value = query_result

    average, count = await reputation(db, uuid.uuid4())

    assert average is None
    assert count == 0
    statement = db.execute.await_args.args[0]
    sql = str(statement.compile()).lower()
    assert "review_moderation_decisions" in sql
    assert "exclude" in statement.compile().params.values()
