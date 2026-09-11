import hashlib
import hmac

from redis.asyncio import Redis

from app.config import settings

PASSWORD_FAILURE_SCRIPT = """
local attempts = redis.call('INCR', KEYS[1])
redis.call('EXPIRE', KEYS[1], ARGV[1])
local delay = 0
if attempts >= tonumber(ARGV[2]) then
    local exponent = attempts - tonumber(ARGV[2])
    delay = tonumber(ARGV[3]) * (2 ^ exponent)
    if delay > tonumber(ARGV[4]) then
        delay = tonumber(ARGV[4])
    end
    redis.call('SET', KEYS[2], '1', 'EX', delay)
end
return delay
"""

PASSWORD_FAILURE_CLEAR_SCRIPT = """
local current = redis.call('GET', KEYS[1])
local current_attempts = current and tonumber(current) or 0
if current_attempts == tonumber(ARGV[1]) then
    redis.call('DEL', KEYS[1], KEYS[2])
    return 1
end
return 0
"""


def auth_identity(phone: str) -> str:
    return hmac.new(
        settings.rate_limit_key_secret.get_secret_value().encode(),
        # This is keyed pseudonymization of a phone identifier for Redis keys;
        # passwords never reach this function.
        phone.encode(),  # lgtm[py/weak-sensitive-data-hashing]
        hashlib.sha256,
    ).hexdigest()


def password_failure_keys(phone: str) -> tuple[str, str]:
    identity = auth_identity(phone)
    return (
        f"rate:auth:password:attempts:{identity}",
        f"rate:auth:password:delay:{identity}",
    )


async def password_retry_after(redis: Redis, phone: str) -> int:
    _, delay_key = password_failure_keys(phone)
    ttl = int(await redis.ttl(delay_key))
    if ttl == -1:
        return settings.auth_account_delay_max_seconds
    return max(0, ttl)


async def password_failure_count(redis: Redis, phone: str) -> int:
    attempts_key, _ = password_failure_keys(phone)
    value = await redis.get(attempts_key)
    return int(value) if value is not None else 0


async def record_password_failure(redis: Redis, phone: str) -> int:
    attempts_key, delay_key = password_failure_keys(phone)
    result = await redis.eval(
        PASSWORD_FAILURE_SCRIPT,
        2,
        attempts_key,
        delay_key,
        settings.auth_account_failure_window_seconds,
        settings.auth_account_delay_after,
        settings.auth_account_delay_base_seconds,
        settings.auth_account_delay_max_seconds,
    )
    return int(result)


async def clear_password_failures(
    redis: Redis,
    phone: str,
    observed_attempts: int,
) -> bool:
    result = await redis.eval(
        PASSWORD_FAILURE_CLEAR_SCRIPT,
        2,
        *password_failure_keys(phone),
        observed_attempts,
    )
    return int(result) == 1
