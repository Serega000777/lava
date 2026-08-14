import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.messaging.schemas import MessageCreate
from app.messaging.service import create_conversation, participant_conversation, send_message
from app.models import Conversation, Listing, Message


def test_message_rejects_blank_body() -> None:
    with pytest.raises(ValidationError):
        MessageCreate(client_message_id=uuid.uuid4(), body="   ")


def test_message_rejects_oversized_body() -> None:
    with pytest.raises(ValidationError):
        MessageCreate(client_message_id=uuid.uuid4(), body="x" * 4001)


@pytest.mark.asyncio
async def test_foreign_conversation_is_hidden() -> None:
    db = AsyncMock()
    db.scalar.return_value = None

    with pytest.raises(HTTPException) as error:
        await participant_conversation(db, uuid.uuid4(), uuid.uuid4())

    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_seller_cannot_start_conversation_with_self() -> None:
    user_id = uuid.uuid4()
    db = AsyncMock()
    db.scalar.return_value = Listing(
        id=uuid.uuid4(),
        owner_id=user_id,
        category_id=uuid.uuid4(),
        title="Товар",
        description="",
        city="Москва",
        status="active",
    )

    with pytest.raises(HTTPException) as error:
        await create_conversation(db, user_id, uuid.uuid4())

    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_idempotency_key_rejects_changed_message_payload() -> None:
    sender_id = uuid.uuid4()
    client_id = uuid.uuid4()
    conversation = Conversation(
        id=uuid.uuid4(),
        listing_id=uuid.uuid4(),
        buyer_id=sender_id,
        seller_id=uuid.uuid4(),
    )
    existing = Message(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        sender_id=sender_id,
        client_message_id=client_id,
        body="Первый текст",
    )
    db = AsyncMock()
    db.scalar.side_effect = [False, None, existing]

    with pytest.raises(HTTPException) as error:
        await send_message(db, conversation, sender_id, client_id, "Другой текст")

    assert error.value.status_code == 409
    db.commit.assert_not_awaited()
