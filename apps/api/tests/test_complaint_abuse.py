import uuid
from unittest.mock import AsyncMock

import pytest

from app.complaints.abuse import complaint_rate_keys, complaint_rate_limited


def test_complaint_rate_keys_do_not_expose_public_identifiers() -> None:
    user_id = uuid.uuid4()
    listing_id = uuid.uuid4()
    request_id = uuid.uuid4()

    keys = complaint_rate_keys(user_id, listing_id, request_id)

    assert all(str(user_id) not in key for key in keys)
    assert all(str(listing_id) not in key for key in keys)
    assert all(str(request_id) not in key for key in keys)


@pytest.mark.asyncio
async def test_new_complaint_within_limit_is_allowed() -> None:
    redis = AsyncMock()
    redis.eval.return_value = 1

    limited = await complaint_rate_limited(
        redis, uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    )

    assert limited is False
    redis.eval.assert_awaited_once()


@pytest.mark.asyncio
async def test_duplicate_request_does_not_report_limit() -> None:
    redis = AsyncMock()
    redis.eval.return_value = 1

    limited = await complaint_rate_limited(
        redis, uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    )

    assert limited is False


@pytest.mark.asyncio
async def test_complaint_over_limit_is_rejected() -> None:
    redis = AsyncMock()
    redis.eval.return_value = 2

    limited = await complaint_rate_limited(
        redis, uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    )

    assert limited is True
