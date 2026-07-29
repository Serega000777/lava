import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.complaints.schemas import AppealCreate, AppealDecision, ComplaintCreate, ComplaintDecision
from app.complaints.service import create_complaint, decide_appeal, decide_complaint
from app.models import Complaint, Listing, ModerationAppeal


def test_complaint_schema_rejects_unknown_reason() -> None:
    with pytest.raises(ValidationError):
        ComplaintCreate(
            client_request_id=uuid.uuid4(),
            reason_code="seller_is_annoying",
        )


def test_appeal_requires_substantive_reason() -> None:
    with pytest.raises(ValidationError):
        AppealCreate(case_id=uuid.uuid4(), reason="Не согласен")


@pytest.mark.asyncio
async def test_owner_cannot_report_own_listing() -> None:
    owner_id = uuid.uuid4()
    db = AsyncMock()
    db.scalar.side_effect = [
        None,
        Listing(
            id=uuid.uuid4(),
            owner_id=owner_id,
            category_id=uuid.uuid4(),
            title="Насос",
            city="Москва",
            status="active",
        ),
    ]

    with pytest.raises(HTTPException) as error:
        await create_complaint(
            db,
            uuid.uuid4(),
            owner_id,
            ComplaintCreate(
                client_request_id=uuid.uuid4(),
                reason_code="fraud",
            ),
        )

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "self_complaint_not_allowed"


@pytest.mark.asyncio
async def test_complaint_retry_returns_existing_record() -> None:
    complaint = Complaint(
        id=uuid.uuid4(),
        listing_id=uuid.uuid4(),
        listing_owner_id=uuid.uuid4(),
        reporter_id=uuid.uuid4(),
        client_request_id=uuid.uuid4(),
        reason_code="fraud",
        details="",
    )
    db = AsyncMock()
    db.scalar.return_value = complaint

    result = await create_complaint(
        db,
        complaint.listing_id,
        complaint.reporter_id,
        ComplaintCreate(
            client_request_id=complaint.client_request_id,
            reason_code="fraud",
        ),
    )

    assert result is complaint
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_complaint_retry_rejects_changed_payload() -> None:
    complaint = Complaint(
        id=uuid.uuid4(),
        listing_id=uuid.uuid4(),
        listing_owner_id=uuid.uuid4(),
        reporter_id=uuid.uuid4(),
        client_request_id=uuid.uuid4(),
        reason_code="fraud",
        details="Запрос предоплаты",
    )
    db = AsyncMock()
    db.scalar.return_value = complaint

    with pytest.raises(HTTPException) as error:
        await create_complaint(
            db,
            complaint.listing_id,
            complaint.reporter_id,
            ComplaintCreate(
                client_request_id=complaint.client_request_id,
                reason_code="duplicate",
            ),
        )

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "idempotency_key_reused"


@pytest.mark.asyncio
async def test_dismissal_rejects_enforcement_resolution_code() -> None:
    with pytest.raises(HTTPException) as error:
        await decide_complaint(
            AsyncMock(),
            uuid.uuid4(),
            uuid.uuid4(),
            ComplaintDecision(
                decision="dismissed",
                resolution_code="listing_restricted",
            ),
        )

    assert error.value.status_code == 422
    assert error.value.detail["code"] == "invalid_resolution_code"


@pytest.mark.asyncio
async def test_original_moderator_cannot_review_appeal() -> None:
    moderator_id = uuid.uuid4()
    db = AsyncMock()
    db.scalar.side_effect = [
        ModerationAppeal(
            id=uuid.uuid4(),
            case_id=uuid.uuid4(),
            appellant_id=uuid.uuid4(),
            reason="Решение не учитывает приложенные характеристики товара.",
            status="open",
        ),
        moderator_id,
    ]

    with pytest.raises(HTTPException) as error:
        await decide_appeal(
            db,
            uuid.uuid4(),
            moderator_id,
            AppealDecision(
                decision="upheld",
                comment="Первоначальное решение соответствует правилам.",
            ),
        )

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "independent_review_required"
