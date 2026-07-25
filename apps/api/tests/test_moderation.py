import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models import ModerationCase
from app.moderation.schemas import DecisionRequest
from app.moderation.service import claim_case


def test_decision_schema_rejects_unknown_action() -> None:
    with pytest.raises(ValidationError):
        DecisionRequest(decision="ban_everyone", reason_code="spam")


@pytest.mark.asyncio
async def test_claim_rejects_already_decided_case() -> None:
    db = AsyncMock()
    db.scalar.return_value = ModerationCase(
        listing_id=uuid.uuid4(), status="approved", assigned_to=None
    )
    with pytest.raises(HTTPException) as error:
        await claim_case(db, uuid.uuid4(), uuid.uuid4())
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_claim_rejects_other_moderator() -> None:
    db = AsyncMock()
    db.scalar.return_value = ModerationCase(
        listing_id=uuid.uuid4(), status="open", assigned_to=uuid.uuid4()
    )
    with pytest.raises(HTTPException) as error:
        await claim_case(db, uuid.uuid4(), uuid.uuid4())
    assert error.value.detail["code"] == "case_already_claimed"

