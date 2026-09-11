import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.message_reports.abuse import message_report_rate_keys
from app.message_reports.schemas import MessageReportCreate, MessageReportDecision
from app.message_reports.service import create_message_report, decide_message_report
from app.models import Message, MessageReport


def test_message_report_keys_hide_identifiers() -> None:
    user_id, message_id, request_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    keys = message_report_rate_keys(user_id, message_id, request_id)
    assert all(str(value) not in ":".join(keys) for value in (user_id, message_id, request_id))


@pytest.mark.asyncio
async def test_non_participant_cannot_discover_message() -> None:
    db = AsyncMock()
    db.scalar.return_value = None
    result = MagicMock()
    result.one_or_none.return_value = None
    db.execute.return_value = result

    with pytest.raises(HTTPException) as error:
        await create_message_report(
            db,
            uuid.uuid4(),
            uuid.uuid4(),
            MessageReportCreate(
                client_request_id=uuid.uuid4(), reason_code="spam", details=""
            ),
        )

    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_sender_cannot_report_own_message() -> None:
    reporter_id = uuid.uuid4()
    message = Message(
        id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        sender_id=reporter_id,
        client_message_id=uuid.uuid4(),
        body="test",
    )
    db = AsyncMock()
    db.scalar.return_value = None
    result = MagicMock()
    result.one_or_none.return_value = (message, MagicMock())
    db.execute.return_value = result

    with pytest.raises(HTTPException) as error:
        await create_message_report(
            db,
            message.id,
            reporter_id,
            MessageReportCreate(
                client_request_id=uuid.uuid4(), reason_code="harassment", details=""
            ),
        )

    assert error.value.status_code == 409
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_report_idempotency_rejects_changed_payload() -> None:
    reporter_id, message_id, request_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    existing = MessageReport(
        id=uuid.uuid4(),
        message_id=message_id,
        reporter_id=reporter_id,
        reported_user_id=uuid.uuid4(),
        client_request_id=request_id,
        reason_code="spam",
        details="",
    )
    db = AsyncMock()
    db.scalar.return_value = existing

    with pytest.raises(HTTPException) as error:
        await create_message_report(
            db,
            message_id,
            reporter_id,
            MessageReportCreate(
                client_request_id=request_id, reason_code="fraud", details=""
            ),
        )

    assert error.value.detail["code"] == "client_request_payload_changed"


@pytest.mark.asyncio
async def test_decided_report_cannot_be_decided_again() -> None:
    report = MessageReport(
        id=uuid.uuid4(),
        message_id=uuid.uuid4(),
        reporter_id=uuid.uuid4(),
        reported_user_id=uuid.uuid4(),
        client_request_id=uuid.uuid4(),
        reason_code="spam",
        details="",
        status="resolved",
    )
    db = AsyncMock()
    db.scalar.return_value = report

    with pytest.raises(HTTPException) as error:
        await decide_message_report(
            db,
            report.id,
            uuid.uuid4(),
            MessageReportDecision(
                decision="dismissed", resolution_code="no_violation", comment=""
            ),
        )

    assert error.value.status_code == 409
