import hashlib
import uuid

from redis.asyncio import Redis

from app.config import settings

COMPLAINT_LIMIT_SCRIPT = """
local is_new = redis.call('SET', KEYS[1], '1', 'EX', ARGV[3], 'NX')
if not is_new then
    return 0
end
local account_count = redis.call('INCR', KEYS[2])
if account_count == 1 then
    redis.call('EXPIRE', KEYS[2], ARGV[3])
end
local target_count = redis.call('INCR', KEYS[3])
if target_count == 1 then
    redis.call('EXPIRE', KEYS[3], ARGV[3])
end
if account_count > tonumber(ARGV[1]) or target_count > tonumber(ARGV[2]) then
    return 2
end
return 1
"""


def complaint_rate_keys(
    user_id: uuid.UUID,
    listing_id: uuid.UUID,
    client_request_id: uuid.UUID,
) -> tuple[str, str, str]:
    identity = hashlib.sha256(str(user_id).encode()).hexdigest()
    target = hashlib.sha256(f"{user_id}:{listing_id}".encode()).hexdigest()
    request = hashlib.sha256(f"{user_id}:{client_request_id}".encode()).hexdigest()
    return (
        f"rate:complaint:request:{request}",
        f"rate:complaint:account:{identity}",
        f"rate:complaint:target:{target}",
    )


async def complaint_rate_limited(
    redis: Redis,
    user_id: uuid.UUID,
    listing_id: uuid.UUID,
    client_request_id: uuid.UUID,
) -> bool:
    result = await redis.eval(
        COMPLAINT_LIMIT_SCRIPT,
        3,
        *complaint_rate_keys(user_id, listing_id, client_request_id),
        settings.complaint_rate_limit,
        settings.complaint_target_rate_limit,
        settings.complaint_rate_window_seconds,
    )
    return int(result) == 2
