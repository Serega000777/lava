import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.listings.schemas import ListingCreate, ListingUpdate
from app.listings.service import owned_listing, update_draft
from app.models import Listing


@pytest.mark.asyncio
async def test_ownership_check_hides_foreign_listing() -> None:
    db = AsyncMock()
    db.scalar.return_value = None
    with pytest.raises(HTTPException) as error:
        await owned_listing(db, uuid.uuid4(), uuid.uuid4())
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_non_draft_cannot_be_edited() -> None:
    listing = Listing(
        owner_id=uuid.uuid4(), category_id=uuid.uuid4(), title="Телефон",
        description="Описание", city="Москва", status="pending_moderation",
    )
    with pytest.raises(HTTPException) as error:
        await update_draft(AsyncMock(), listing, ListingUpdate(title="Новое название"))
    assert error.value.status_code == 409


def test_listing_rejects_negative_price() -> None:
    with pytest.raises(ValueError):
        ListingCreate(
            category_id=uuid.uuid4(), title="Товар", description="", price=-1,
            city="Москва", attributes={},
        )
