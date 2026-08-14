import hashlib
import uuid

from redis.asyncio import Redis

from app.complaints.abuse import COMPLAINT_LIMIT_SCRIPT
from app.config import settings


def message_report_rate_keys(
    user_id: uuid.UUID, message_id: uuid.UUID, request_id: uuid.UUID
) -> tuple[str, str, str]:
    identity = hashlib.sha256(str(user_id).encode()).hexdigest()
    target = hashlib.sha256(f"{user_id}:{message_id}".encode()).hexdigest()
    request = hashlib.sha256(f"{user_id}:{request_id}".encode()).hexdigest()
    return (
        f"rate:message-report:request:{request}",
        f"rate:message-report:account:{identity}",
        f"rate:message-report:target:{target}",
    )


async def message_report_rate_limited(
    redis: Redis, user_id: uuid.UUID, message_id: uuid.UUID, request_id: uuid.UUID
) -> bool:
    result = await redis.eval(
        COMPLAINT_LIMIT_SCRIPT,
        3,
        *message_report_rate_keys(user_id, message_id, request_id),
        settings.complaint_rate_limit,
        settings.complaint_target_rate_limit,
        settings.complaint_rate_window_seconds,
    )
    return int(result) == 2
