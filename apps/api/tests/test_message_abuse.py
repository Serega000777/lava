import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from redis.exceptions import ConnectionError as RedisConnectionError

from app.messaging.abuse import message_rate_keys, message_rate_limited
from app.messaging.router import create_message
from app.messaging.schemas import MessageCreate
from app.models import Conversation, User


def test_message_rate_keys_do_not_expose_identifiers() -> None:
    user_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    request_id = uuid.uuid4()

    keys = message_rate_keys(user_id, conversation_id, request_id)

    assert all(str(user_id) not in key for key in keys)
    assert all(str(conversation_id) not in key for key in keys)
    assert all(str(request_id) not in key for key in keys)


@pytest.mark.asyncio
async def test_idempotent_allowed_message_retry_does_not_report_limit() -> None:
    redis = AsyncMock()
    redis.eval.return_value = 1

    limited = await message_rate_limited(
        redis, uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    )

    assert limited is False
    redis.eval.assert_awaited_once()


@pytest.mark.asyncio
async def test_idempotent_limited_message_retry_remains_limited() -> None:
    redis = AsyncMock()
    redis.eval.return_value = 2

    limited = await message_rate_limited(
        redis, uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    )

    assert limited is True


@pytest.mark.asyncio
async def test_message_route_returns_retry_after_when_limited(monkeypatch) -> None:
    async def limited(*_args) -> bool:
        return True

    redis = AsyncMock()
    monkeypatch.setattr("app.messaging.router.Redis.from_url", lambda _url: redis)
    monkeypatch.setattr("app.messaging.router.message_rate_limited", limited)
    conversation = Conversation(
        id=uuid.uuid4(),
        listing_id=uuid.uuid4(),
        buyer_id=uuid.uuid4(),
        seller_id=uuid.uuid4(),
    )
    monkeypatch.setattr(
        "app.messaging.router.participant_conversation",
        AsyncMock(return_value=conversation),
    )
    monkeypatch.setattr(
        "app.messaging.router.ensure_messaging_allowed", AsyncMock(return_value=None)
    )

    with pytest.raises(HTTPException) as error:
        await create_message(
            conversation.id,
            MessageCreate(client_message_id=uuid.uuid4(), body="Здравствуйте"),
            User(id=conversation.buyer_id, phone="+79990000005", display_name="Покупатель"),
            AsyncMock(),
        )

    assert error.value.status_code == 429
    assert error.value.headers is not None
    assert "Retry-After" in error.value.headers
    redis.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_message_route_fails_closed_without_redis(monkeypatch) -> None:
    async def unavailable(*_args) -> bool:
        raise RedisConnectionError("redis unavailable")

    redis = AsyncMock()
    monkeypatch.setattr("app.messaging.router.Redis.from_url", lambda _url: redis)
    monkeypatch.setattr("app.messaging.router.message_rate_limited", unavailable)
    conversation = Conversation(
        id=uuid.uuid4(),
        listing_id=uuid.uuid4(),
        buyer_id=uuid.uuid4(),
        seller_id=uuid.uuid4(),
    )
    monkeypatch.setattr(
        "app.messaging.router.participant_conversation",
        AsyncMock(return_value=conversation),
    )
    monkeypatch.setattr(
        "app.messaging.router.ensure_messaging_allowed", AsyncMock(return_value=None)
    )

    with pytest.raises(HTTPException) as error:
        await create_message(
            conversation.id,
            MessageCreate(client_message_id=uuid.uuid4(), body="Здравствуйте"),
            User(id=conversation.buyer_id, phone="+79990000006", display_name="Покупатель"),
            AsyncMock(),
        )

    assert error.value.status_code == 503
    assert error.value.detail["code"] == "security_dependency_unavailable"
    redis.aclose.assert_awaited_once()
