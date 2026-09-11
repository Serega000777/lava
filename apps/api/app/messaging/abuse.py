import hashlib
import uuid

from redis.asyncio import Redis

from app.config import settings

MESSAGE_LIMIT_SCRIPT = """
local prior_decision = redis.call('GET', KEYS[1])
if prior_decision then
    return tonumber(prior_decision)
end
local account_count = redis.call('INCR', KEYS[2])
if account_count == 1 then
    redis.call('EXPIRE', KEYS[2], ARGV[3])
end
local conversation_count = redis.call('INCR', KEYS[3])
if conversation_count == 1 then
    redis.call('EXPIRE', KEYS[3], ARGV[3])
end
if account_count > tonumber(ARGV[1]) or conversation_count > tonumber(ARGV[2]) then
    redis.call('SET', KEYS[1], '2', 'EX', ARGV[3])
    return 2
end
redis.call('SET', KEYS[1], '1', 'EX', ARGV[3])
return 1
"""


def message_rate_keys(
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
    client_message_id: uuid.UUID,
) -> tuple[str, str, str]:
    identity = hashlib.sha256(str(user_id).encode()).hexdigest()
    target = hashlib.sha256(f"{user_id}:{conversation_id}".encode()).hexdigest()
    request = hashlib.sha256(f"{user_id}:{client_message_id}".encode()).hexdigest()
    return (
        f"rate:message:request:{request}",
        f"rate:message:account:{identity}",
        f"rate:message:conversation:{target}",
    )


async def message_rate_limited(
    redis: Redis,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
    client_message_id: uuid.UUID,
) -> bool:
    result = await redis.eval(
        MESSAGE_LIMIT_SCRIPT,
        3,
        *message_rate_keys(user_id, conversation_id, client_message_id),
        settings.message_rate_limit,
        settings.message_conversation_rate_limit,
        settings.message_rate_window_seconds,
    )
    return int(result) == 2
