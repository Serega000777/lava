import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.models import User
from app.verification.schemas import PublicTrustProfile
from app.verification.service import set_verification_level, trust_badge


def test_public_badges_do_not_overstate_verification() -> None:
    assert trust_badge(0, "user") == "Новый"
    assert trust_badge(1, "user") == "Телефон подтверждён"
    assert trust_badge(3, "user") == "Расширенная проверка"
    assert trust_badge(4, "company") == "Проверенная компания"


def test_public_profile_schema_has_no_phone_or_internal_evidence() -> None:
    assert "phone" not in PublicTrustProfile.model_fields
    assert "actor_id" not in PublicTrustProfile.model_fields
    assert "reason_code" not in PublicTrustProfile.model_fields


@pytest.mark.asyncio
async def test_organization_level_requires_company_role() -> None:
    user = User(
        id=uuid.uuid4(),
        phone="+79990000001",
        display_name="Продавец",
        role="user",
        verification_level=2,
    )
    db = AsyncMock()
    db.add = MagicMock()
    db.scalar.return_value = user

    with pytest.raises(HTTPException) as error:
        await set_verification_level(
            db,
            user.id,
            uuid.uuid4(),
            4,
            "organization_confirmed",
        )

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "organization_level_requires_company"
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_verification_change_creates_audit_decision() -> None:
    user = User(
        id=uuid.uuid4(),
        phone="+79990000002",
        display_name="Компания",
        role="company",
        verification_level=2,
    )
    db = AsyncMock()
    db.add = MagicMock()
    db.scalar.return_value = user

    decision = await set_verification_level(
        db,
        user.id,
        uuid.uuid4(),
        4,
        "organization_confirmed",
    )

    assert user.verification_level == 4
    assert decision.previous_level == 2
    assert decision.new_level == 4
    db.add.assert_called_once_with(decision)
    db.commit.assert_awaited_once()
