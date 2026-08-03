from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest

from app.analytics.service import queue_metrics
from app.queueing.service import enqueue_notification_created, notification_dispatch_fields


@pytest.mark.asyncio
async def test_enqueue_notification_uses_idempotent_outbox_insert() -> None:
    db = AsyncMock()
    notification_id = uuid.uuid4()

    await enqueue_notification_created(
        db,
        notification_id=notification_id,
        user_id=uuid.uuid4(),
        kind="new_message",
    )

    statement = db.execute.await_args.args[0]
    assert "ON CONFLICT (topic, source_key) DO NOTHING" in str(statement)
    assert str(notification_id) in statement.compile().params.values()


def test_notification_dispatch_fields_validate_and_hash_subject() -> None:
    user_id = uuid.uuid4()
    notification_id = uuid.uuid4()

    subject, parsed_notification_id, kind = notification_dispatch_fields(
        {
            "user_id": str(user_id),
            "notification_id": str(notification_id),
            "kind": "new_message",
        }
    )

    assert str(user_id) not in subject
    assert len(subject) == 64
    assert parsed_notification_id == str(notification_id)
    assert kind == "new_message"


def test_notification_dispatch_fields_reject_unknown_kind() -> None:
    with pytest.raises(ValueError, match="invalid_payload"):
        notification_dispatch_fields(
            {
                "user_id": str(uuid.uuid4()),
                "notification_id": str(uuid.uuid4()),
                "kind": "password_reset",
            }
        )


@pytest.mark.asyncio
async def test_queue_metrics_marks_fresh_heartbeat_healthy() -> None:
    now = datetime.now(UTC)
    mappings = MagicMock()
    mappings.one.return_value = {
        "pending": 2,
        "processing": 1,
        "failed": 3,
        "completed": 5,
        "oldest_pending_at": now - timedelta(seconds=12),
    }
    result = MagicMock()
    result.mappings.return_value = mappings
    db = AsyncMock()
    db.execute.return_value = result

    metrics = await queue_metrics(db, int(now.timestamp()))

    assert metrics["worker_healthy"] is True
    assert metrics["oldest_pending_seconds"] >= 12
    assert metrics["failed"] == 3


@pytest.mark.asyncio
async def test_queue_metrics_reports_missing_heartbeat_without_failing() -> None:
    mappings = MagicMock()
    mappings.one.return_value = {
        "pending": 0,
        "processing": 0,
        "failed": 0,
        "completed": 0,
        "oldest_pending_at": None,
    }
    result = MagicMock()
    result.mappings.return_value = mappings
    db = AsyncMock()
    db.execute.return_value = result

    metrics = await queue_metrics(db, None)

    assert metrics["worker_healthy"] is False
    assert metrics["heartbeat_age_seconds"] is None
