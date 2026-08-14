import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.messaging.schemas import MessageCreate
from app.messaging.service import (
    create_conversation,
    mute_conversation,
    mark_conversation_read,
    participant_conversation,
    send_message,
)
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


@pytest.mark.asyncio
async def test_foreign_conversation_cannot_be_muted() -> None:
    db = AsyncMock()
    db.scalar.return_value = None

    with pytest.raises(HTTPException) as error:
        await mute_conversation(db, uuid.uuid4(), uuid.uuid4())

    assert error.value.status_code == 404
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_muted_recipient_gets_message_without_notification(monkeypatch) -> None:
    sender_id = uuid.uuid4()
    conversation = Conversation(
        id=uuid.uuid4(),
        listing_id=uuid.uuid4(),
        buyer_id=sender_id,
        seller_id=uuid.uuid4(),
    )
    message = Message(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        sender_id=sender_id,
        client_message_id=uuid.uuid4(),
        body="Здравствуйте",
    )
    db = AsyncMock()
    db.scalar.side_effect = [False, message.id, message, True]
    enqueue = AsyncMock()
    monkeypatch.setattr("app.messaging.service.enqueue_notification_created", enqueue)

    result = await send_message(
        db, conversation, sender_id, message.client_message_id, message.body
    )

    assert result is message
    assert db.scalar.await_count == 4
    enqueue.assert_not_awaited()
    assert conversation.updated_at is not None
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_read_receipt_is_idempotent_when_nothing_is_unread() -> None:
    conversation = Conversation(
        id=uuid.uuid4(),
        listing_id=uuid.uuid4(),
        buyer_id=uuid.uuid4(),
        seller_id=uuid.uuid4(),
    )
    scalars = MagicMock()
    scalars.all.return_value = []
    db = AsyncMock()
    db.scalars.return_value = scalars

    result = await mark_conversation_read(db, conversation, conversation.buyer_id)

    assert result == {"read_count": 0, "read_at": None}
    db.execute.assert_not_awaited()
    db.commit.assert_not_awaited()
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_read_receipt_updates_selected_incoming_messages() -> None:
    conversation = Conversation(
        id=uuid.uuid4(),
        listing_id=uuid.uuid4(),
        buyer_id=uuid.uuid4(),
        seller_id=uuid.uuid4(),
    )
    unread_ids = [uuid.uuid4(), uuid.uuid4()]
    scalars = MagicMock()
    scalars.all.return_value = unread_ids
    db = AsyncMock()
    db.scalars.return_value = scalars

    result = await mark_conversation_read(db, conversation, conversation.buyer_id)

    assert result["read_count"] == 2
    assert result["read_at"].tzinfo is not None
    statement = db.scalars.await_args.args[0]
    compiled = statement.compile()
    assert conversation.id in compiled.params.values()
    assert conversation.buyer_id in compiled.params.values()
    db.execute.assert_not_awaited()
    db.commit.assert_awaited_once()
