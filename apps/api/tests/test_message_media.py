import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.message_media.service import (
    ensure_message_media_mutable,
    list_participant_message_media,
    next_message_media_position,
    owned_message_for_media,
    participant_media,
)
from app.media.storage import S3Storage
from app.models import Conversation, Message


@pytest.mark.asyncio
async def test_only_sender_can_upload_to_message() -> None:
    db = AsyncMock()
    db.scalar.return_value = None

    with pytest.raises(HTTPException) as error:
        await owned_message_for_media(db, uuid.uuid4(), uuid.uuid4())

    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_foreign_participant_cannot_list_message_media() -> None:
    db = AsyncMock()
    db.scalar.return_value = None

    with pytest.raises(HTTPException) as error:
        await list_participant_message_media(db, uuid.uuid4(), uuid.uuid4())

    assert error.value.status_code == 404
    db.scalars.assert_not_awaited()


@pytest.mark.asyncio
async def test_foreign_participant_cannot_download_media() -> None:
    db = AsyncMock()
    db.scalar.return_value = None

    with pytest.raises(HTTPException) as error:
        await participant_media(db, uuid.uuid4(), uuid.uuid4())

    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_message_media_limit_is_enforced() -> None:
    scalars = MagicMock()
    scalars.all.return_value = [0, 1, 2]
    db = AsyncMock()
    db.scalars.return_value = scalars

    with pytest.raises(HTTPException) as error:
        await next_message_media_position(db, uuid.uuid4())

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "message_media_limit_reached"


@pytest.mark.asyncio
async def test_reported_message_media_is_locked(monkeypatch) -> None:
    user_id = uuid.uuid4()
    conversation = Conversation(
        id=uuid.uuid4(),
        listing_id=uuid.uuid4(),
        buyer_id=user_id,
        seller_id=uuid.uuid4(),
    )
    message = Message(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        sender_id=user_id,
        client_message_id=uuid.uuid4(),
        body="test",
    )
    allowed = AsyncMock()
    monkeypatch.setattr("app.message_media.service.ensure_messaging_allowed", allowed)
    db = AsyncMock()
    db.get.return_value = conversation
    db.scalar.return_value = uuid.uuid4()

    with pytest.raises(HTTPException) as error:
        await ensure_message_media_mutable(db, message, user_id)

    assert error.value.detail["code"] == "reported_message_media_locked"
    allowed.assert_awaited_once()


def test_private_message_media_has_no_store_cache_policy() -> None:
    client = MagicMock()
    storage = S3Storage(client)

    storage.put("messages/test.webp", b"image", "image/webp", "private, no-store")

    extra_args = client.upload_fileobj.call_args.kwargs["ExtraArgs"]
    assert extra_args == {
        "ContentType": "image/webp",
        "CacheControl": "private, no-store",
    }
