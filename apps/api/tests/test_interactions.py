from datetime import UTC, datetime
import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.interactions.service import confirm_interaction, interaction_status
from app.models import Conversation, Interaction


def conversation_for(buyer_id: uuid.UUID | None = None) -> Conversation:
    return Conversation(
        id=uuid.uuid4(),
        listing_id=uuid.uuid4(),
        buyer_id=buyer_id or uuid.uuid4(),
        seller_id=uuid.uuid4(),
    )


@pytest.mark.asyncio
async def test_interaction_status_is_participant_relative() -> None:
    conversation = conversation_for()
    interaction = Interaction(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        contacted_at=datetime.now(UTC),
        buyer_confirmed_at=datetime.now(UTC),
    )
    db = AsyncMock()
    db.scalar.side_effect = [conversation, interaction, False]

    result = await interaction_status(db, conversation.id, conversation.seller_id)

    assert result["status"] == "contacted"
    assert result["my_completion_confirmed"] is False
    assert result["counterpart_completion_confirmed"] is True
    assert result["can_review"] is False


@pytest.mark.asyncio
async def test_interaction_cannot_be_confirmed_before_contact() -> None:
    conversation = conversation_for()
    interaction = Interaction(id=uuid.uuid4(), conversation_id=conversation.id)
    db = AsyncMock()
    db.scalar.side_effect = [conversation, interaction]

    with pytest.raises(HTTPException) as error:
        await confirm_interaction(db, conversation.id, conversation.buyer_id)

    assert error.value.status_code == 409
    assert error.value.detail == {"code": "interaction_not_started"}
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_second_confirmation_completes_interaction() -> None:
    conversation = conversation_for()
    interaction = Interaction(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        contacted_at=datetime.now(UTC),
        buyer_confirmed_at=datetime.now(UTC),
    )
    db = AsyncMock()
    db.scalar.side_effect = [conversation, interaction, False]

    result = await confirm_interaction(db, conversation.id, conversation.seller_id)

    assert interaction.seller_confirmed_at is not None
    assert interaction.completed_at == interaction.seller_confirmed_at
    assert result["status"] == "completed"
    assert result["can_review"] is True
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_repeated_confirmation_is_idempotent() -> None:
    conversation = conversation_for()
    completed_at = datetime.now(UTC)
    interaction = Interaction(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        contacted_at=completed_at,
        buyer_confirmed_at=completed_at,
        seller_confirmed_at=completed_at,
        completed_at=completed_at,
    )
    db = AsyncMock()
    db.scalar.side_effect = [conversation, interaction, True]

    result = await confirm_interaction(db, conversation.id, conversation.buyer_id)

    assert interaction.buyer_confirmed_at == completed_at
    assert interaction.completed_at == completed_at
    assert result["review_created"] is True
    assert result["can_review"] is False
    db.commit.assert_awaited_once()
