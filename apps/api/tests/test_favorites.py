import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.favorites.service import add_favorite, remove_favorite


@pytest.mark.asyncio
async def test_inactive_or_missing_listing_cannot_be_favorited() -> None:
    db = AsyncMock()
    db.scalar.return_value = None

    with pytest.raises(HTTPException) as error:
        await add_favorite(db, uuid.uuid4(), uuid.uuid4())

    assert error.value.status_code == 404
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_remove_favorite_is_idempotent() -> None:
    db = AsyncMock()

    await remove_favorite(db, uuid.uuid4(), uuid.uuid4())

    db.execute.assert_awaited_once()
    db.commit.assert_awaited_once()
