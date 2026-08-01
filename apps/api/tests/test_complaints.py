import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from redis.exceptions import ConnectionError as RedisConnectionError

from app.complaints.router import report_listing
from app.complaints.schemas import AppealCreate, AppealDecision, ComplaintCreate, ComplaintDecision
from app.complaints.service import (
    ComplaintSignalInput,
    assess_complaint_coordination,
    create_complaint,
    decide_appeal,
    decide_complaint,
)
from app.models import Complaint, Listing, ModerationAppeal, User


def test_complaint_schema_rejects_unknown_reason() -> None:
    with pytest.raises(ValidationError):
        ComplaintCreate(
            client_request_id=uuid.uuid4(),
            reason_code="seller_is_annoying",
        )


def test_appeal_requires_substantive_reason() -> None:
    with pytest.raises(ValidationError):
        AppealCreate(case_id=uuid.uuid4(), reason="Не согласен")


def test_coordination_signal_requires_multiple_explainable_indicators() -> None:
    now = datetime.now(UTC)
    reports = [
        ComplaintSignalInput(uuid.uuid4(), "fraud", now - timedelta(days=1))
        for _ in range(3)
    ]

    signal = assess_complaint_coordination(reports, now=now)

    assert signal["detected"] is True
    assert signal["reporter_count"] == 3
    assert signal["indicators"] == [
        "reporter_burst",
        "reason_concentration",
        "new_account_cluster",
    ]


def test_coordination_signal_deduplicates_reporters_and_avoids_weak_alerts() -> None:
    now = datetime.now(UTC)
    reporter_id = uuid.uuid4()
    reports = [
        ComplaintSignalInput(reporter_id, "fraud", now - timedelta(days=30)),
        ComplaintSignalInput(reporter_id, "duplicate", now - timedelta(days=30)),
    ]

    signal = assess_complaint_coordination(reports, now=now)

    assert signal["detected"] is False
    assert signal["reporter_count"] == 1
    assert signal["dominant_reason_code"] == "fraud"
    assert signal["indicators"] == []


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


@pytest.mark.asyncio
async def test_complaint_route_returns_retry_after_when_limited(monkeypatch) -> None:
    async def limited(*_args) -> bool:
        return True

    redis = AsyncMock()
    monkeypatch.setattr("app.complaints.router.Redis.from_url", lambda _url: redis)
    monkeypatch.setattr("app.complaints.router.complaint_rate_limited", limited)
    user = User(
        id=uuid.uuid4(),
        phone="+79990000003",
        display_name="Покупатель",
    )

    with pytest.raises(HTTPException) as error:
        await report_listing(
            uuid.uuid4(),
            ComplaintCreate(
                client_request_id=uuid.uuid4(),
                reason_code="fraud",
            ),
            user,
            AsyncMock(),
        )

    assert error.value.status_code == 429
    assert error.value.detail["code"] == "complaint_rate_limited"
    assert error.value.headers is not None
    assert "Retry-After" in error.value.headers
    redis.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_complaint_route_fails_closed_without_redis(monkeypatch) -> None:
    async def unavailable(*_args) -> bool:
        raise RedisConnectionError("redis unavailable")

    redis = AsyncMock()
    monkeypatch.setattr("app.complaints.router.Redis.from_url", lambda _url: redis)
    monkeypatch.setattr("app.complaints.router.complaint_rate_limited", unavailable)
    user = User(
        id=uuid.uuid4(),
        phone="+79990000004",
        display_name="Покупатель",
    )

    with pytest.raises(HTTPException) as error:
        await report_listing(
            uuid.uuid4(),
            ComplaintCreate(
                client_request_id=uuid.uuid4(),
                reason_code="fraud",
            ),
            user,
            AsyncMock(),
        )

    assert error.value.status_code == 503
    assert error.value.detail["code"] == "security_dependency_unavailable"
    redis.aclose.assert_awaited_once()
