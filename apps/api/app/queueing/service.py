import hashlib
import uuid

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OutboxTask

NOTIFICATION_KINDS = frozenset({"new_conversation", "new_message"})


def notification_dispatch_fields(payload: dict[str, object]) -> tuple[str, str, str]:
    try:
        user_id = uuid.UUID(str(payload["user_id"]))
        notification_id = uuid.UUID(str(payload["notification_id"]))
        kind = str(payload["kind"])
    except (KeyError, ValueError) as error:
        raise ValueError("invalid_payload") from error
    if kind not in NOTIFICATION_KINDS:
        raise ValueError("invalid_payload")
    stream_subject = hashlib.sha256(str(user_id).encode()).hexdigest()
    return stream_subject, str(notification_id), kind


async def enqueue_notification_created(
    db: AsyncSession,
    *,
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
    kind: str,
) -> None:
    await db.execute(
        insert(OutboxTask)
        .values(
            id=uuid.uuid4(),
            topic="notification.created",
            source_key=str(notification_id),
            payload={
                "notification_id": str(notification_id),
                "user_id": str(user_id),
                "kind": kind,
            },
        )
        .on_conflict_do_nothing(index_elements=["topic", "source_key"])
    )
