from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, Response
from pydantic import ValidationError
from redis.exceptions import ConnectionError as RedisConnectionError

from app.auth.abuse import (
    auth_identity,
    clear_password_failures,
    password_failure_count,
    password_failure_keys,
    password_retry_after,
    record_password_failure,
)
from app.auth.router import password_login
from app.auth.schemas import PasswordLoginRequest
from app.auth.service import authenticate_password, authenticate_password_with_delay
from app.config import Settings
from app.models import User


def test_password_failure_keys_are_stable_and_hide_phone() -> None:
    phone = "+79990000000"

    first = password_failure_keys(phone)
    second = password_failure_keys(phone)

    assert first == second
    assert all(phone not in key for key in first)
    assert first[0] != first[1]
    assert auth_identity(phone) in first[0]


def test_account_delay_configuration_rejects_inverted_range() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            auth_account_delay_base_seconds=60,
            auth_account_delay_max_seconds=10,
        )
    with pytest.raises(ValidationError):
        Settings(_env_file=None, rate_limit_key_secret="too-short")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production")


@pytest.mark.asyncio
async def test_password_failure_delay_uses_atomic_bounded_policy() -> None:
    redis = AsyncMock()
    redis.eval.return_value = 8

    delay = await record_password_failure(redis, "+79990000000")

    assert delay == 8
    args = redis.eval.await_args.args
    assert args[1] == 2
    assert args[-4:] == (3_600, 3, 2, 300)
    assert "+79990000000" not in " ".join(str(value) for value in args)


@pytest.mark.asyncio
async def test_password_retry_after_normalizes_missing_key() -> None:
    redis = AsyncMock()
    redis.ttl.side_effect = [-2, -1, 17]

    assert await password_retry_after(redis, "+79990000000") == 0
    assert await password_retry_after(redis, "+79990000000") == 300
    assert await password_retry_after(redis, "+79990000000") == 17


@pytest.mark.asyncio
async def test_password_failure_count_defaults_to_zero() -> None:
    redis = AsyncMock()
    redis.get.side_effect = [None, b"4"]

    assert await password_failure_count(redis, "+79990000000") == 0
    assert await password_failure_count(redis, "+79990000000") == 4


@pytest.mark.asyncio
async def test_active_account_delay_skips_password_work(monkeypatch) -> None:
    db = AsyncMock()
    redis = AsyncMock()
    authenticate = AsyncMock()
    monkeypatch.setattr("app.auth.service.password_retry_after", AsyncMock(return_value=12))
    monkeypatch.setattr("app.auth.service.authenticate_password", authenticate)

    with pytest.raises(HTTPException) as error:
        await authenticate_password_with_delay(db, redis, "+79990000000", "Wrong12345")

    assert error.value.status_code == 429
    assert error.value.headers == {"Retry-After": "12"}
    authenticate.assert_not_awaited()


@pytest.mark.asyncio
async def test_failed_password_activates_progressive_delay(monkeypatch) -> None:
    db = AsyncMock()
    redis = AsyncMock()
    invalid = HTTPException(401, detail={"code": "invalid_credentials"})
    monkeypatch.setattr(
        "app.auth.service.password_retry_after", AsyncMock(return_value=0)
    )
    monkeypatch.setattr(
        "app.auth.service.password_failure_count", AsyncMock(return_value=0)
    )
    monkeypatch.setattr(
        "app.auth.service.authenticate_password", AsyncMock(side_effect=invalid)
    )
    monkeypatch.setattr(
        "app.auth.service.record_password_failure", AsyncMock(return_value=2)
    )

    with pytest.raises(HTTPException) as error:
        await authenticate_password_with_delay(db, redis, "+79990000000", "Wrong12345")

    assert error.value.status_code == 429
    assert error.value.detail["code"] == "account_login_delayed"
    assert error.value.headers == {"Retry-After": "2"}


@pytest.mark.asyncio
async def test_successful_password_clears_account_failures(monkeypatch) -> None:
    db = AsyncMock()
    redis = AsyncMock()
    user = User(phone="+79990000000", display_name="Иван")
    clear = AsyncMock()
    monkeypatch.setattr("app.auth.service.password_retry_after", AsyncMock(return_value=0))
    monkeypatch.setattr("app.auth.service.password_failure_count", AsyncMock(return_value=2))
    monkeypatch.setattr("app.auth.service.authenticate_password", AsyncMock(return_value=user))
    monkeypatch.setattr("app.auth.service.clear_password_failures", clear)

    result = await authenticate_password_with_delay(
        db, redis, "+79990000000", "Reliable123"
    )

    assert result is user
    clear.assert_awaited_once_with(redis, "+79990000000", 2)


@pytest.mark.asyncio
async def test_unknown_account_still_runs_password_verification(monkeypatch) -> None:
    db = AsyncMock()
    result = MagicMock()
    result.one_or_none.return_value = None
    db.execute.return_value = result
    verify = MagicMock(return_value=False)
    monkeypatch.setattr("app.auth.service.verify_password", verify)

    with pytest.raises(HTTPException) as error:
        await authenticate_password(db, "+79990000000", "Wrong12345")

    assert error.value.status_code == 401
    verify.assert_called_once()


@pytest.mark.asyncio
async def test_login_fails_closed_if_account_limiter_breaks(monkeypatch) -> None:
    redis = AsyncMock()
    monkeypatch.setattr("app.auth.router.Redis.from_url", lambda _: redis)
    monkeypatch.setattr(
        "app.auth.router.authenticate_password_with_delay",
        AsyncMock(side_effect=RedisConnectionError("redis unavailable")),
    )

    with pytest.raises(HTTPException) as error:
        await password_login(
            PasswordLoginRequest(phone="+79990000000", password="Reliable123"),
            Response(),
            AsyncMock(),
        )

    assert error.value.status_code == 503
    assert error.value.detail["code"] == "security_dependency_unavailable"
    redis.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_clear_password_failures_is_compare_and_delete_safe() -> None:
    redis = AsyncMock()
    redis.eval.return_value = 1

    cleared = await clear_password_failures(redis, "+79990000000", 2)

    assert cleared is True
    args = redis.eval.await_args.args
    assert args[1] == 2
    assert args[2:4] == password_failure_keys("+79990000000")
    assert args[4] == 2
