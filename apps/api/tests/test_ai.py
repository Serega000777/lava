import uuid

import pytest
from pydantic import ValidationError

from app.ai.provider import LocalSafeTextProvider
from app.ai.schemas import GenerationRequest


def test_generation_requires_uuid_idempotency_key() -> None:
    with pytest.raises(ValidationError):
        GenerationRequest(client_request_id="not-a-uuid")


@pytest.mark.asyncio
async def test_local_provider_does_not_invent_listing_facts() -> None:
    result = await LocalSafeTextProvider().improve_listing({
        "title": "  Велосипед  ",
        "description": "  Есть царапина.  ",
        "category_id": str(uuid.uuid4()),
        "attributes": {},
    })
    assert result.title == "Велосипед"
    assert result.description == "Есть царапина."
