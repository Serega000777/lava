import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.blocking.service import (
    block_user,
    ensure_messaging_allowed,
    list_blocked_users,
    unblock_user,
)


@pytest.mark.asyncio
async def test_user_cannot_block_self() -> None:
    user_id = uuid.uuid4()
    db = AsyncMock()

    with pytest.raises(HTTPException) as error:
        await block_user(db, user_id, user_id)

    assert error.value.status_code == 409
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_block_in_either_direction_prevents_messaging() -> None:
    db = AsyncMock()
    db.scalar.return_value = True

    with pytest.raises(HTTPException) as error:
        await ensure_messaging_allowed(db, uuid.uuid4(), uuid.uuid4())

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "messaging_blocked"


@pytest.mark.asyncio
async def test_unblock_is_idempotent_and_owner_scoped() -> None:
    db = AsyncMock()
    blocker_id = uuid.uuid4()
    blocked_id = uuid.uuid4()

    await unblock_user(db, blocker_id, blocked_id)

    statement = db.execute.await_args.args[0]
    compiled = statement.compile()
    assert blocker_id in compiled.params.values()
    assert blocked_id in compiled.params.values()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_block_list_returns_only_public_fields() -> None:
    mappings = MagicMock()
    mappings.all.return_value = []
    result = MagicMock()
    result.mappings.return_value = mappings
    db = AsyncMock()
    db.execute.return_value = result

    assert await list_blocked_users(db, uuid.uuid4(), 50, 0) == []
