import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.auth.schemas import PasswordRecoveryConfirm, SessionResponse
from app.auth.router import revoke_session
from app.auth.security import hash_password, hash_token, verify_password
from app.auth.service import (
    otp_key,
    request_otp,
    reset_password_and_revoke_sessions,
    verify_otp,
)
from app.models import PasswordCredential, Session, User


def test_recovery_password_uses_registration_strength_rules() -> None:
    with pytest.raises(ValueError):
        PasswordRecoveryConfirm(
            phone="+79990000000",
            code="123456",
            new_password="onlyletters",
        )


def test_session_response_excludes_token_hash() -> None:
    assert "token_hash" not in SessionResponse.model_fields
    assert set(SessionResponse.model_fields) == {
        "id",
        "created_at",
        "expires_at",
        "is_current",
    }


@pytest.mark.asyncio
async def test_login_and_recovery_otp_use_separate_keys() -> None:
    redis = AsyncMock()
    redis.incr.return_value = 1
    redis.get.return_value = None
    phone = "+79990000000"

    await request_otp(redis, phone, purpose="login")
    await request_otp(redis, phone, purpose="recovery")

    stored_keys = [call.args[0] for call in redis.setex.await_args_list]
    assert otp_key("login", phone) in stored_keys
    assert otp_key("recovery", phone) in stored_keys
    assert otp_key("login", phone) != otp_key("recovery", phone)
    reset_keys = [call.args[0] for call in redis.delete.await_args_list]
    assert f"{otp_key('login', phone)}:attempts" in reset_keys
    assert f"{otp_key('recovery', phone)}:attempts" in reset_keys


@pytest.mark.asyncio
async def test_login_code_cannot_confirm_recovery() -> None:
    phone = "+79990000000"
    code = "123456"
    redis = AsyncMock()
    redis.incr.return_value = 1

    async def get_value(key: str):
        if key == otp_key("login", phone):
            return hash_token(code).encode()
        return None

    redis.get.side_effect = get_value

    assert await verify_otp(redis, phone, code, purpose="recovery") is False
    redis.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_otp_is_destroyed_after_attempt_limit() -> None:
    redis = AsyncMock()
    redis.incr.return_value = 6
    phone = "+79990000000"

    assert await verify_otp(redis, phone, "123456", purpose="recovery") is False

    redis.delete.assert_awaited_once_with(otp_key("recovery", phone))
    redis.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_password_reset_revokes_existing_sessions() -> None:
    user = User(
        id=uuid.uuid4(),
        phone="+79990000000",
        display_name="Пользователь",
        is_active=True,
    )
    credential = PasswordCredential(
        user_id=user.id,
        password_hash=hash_password("OldPassword123"),
    )
    db = AsyncMock()
    db.add = MagicMock()
    db.scalar.return_value = user
    db.get.return_value = credential

    result = await reset_password_and_revoke_sessions(
        db,
        user.phone,
        "NewPassword123",
    )

    assert result is user
    assert verify_password(credential.password_hash, "NewPassword123")
    assert not verify_password(credential.password_hash, "OldPassword123")
    db.execute.assert_awaited_once()
    db.commit.assert_awaited_once()


def test_session_response_marks_only_current_session() -> None:
    now = datetime.now(UTC)
    response = SessionResponse(
        id=uuid.uuid4(),
        created_at=now,
        expires_at=now + timedelta(hours=1),
        is_current=True,
    )
    assert response.is_current is True


@pytest.mark.asyncio
async def test_current_session_requires_explicit_logout() -> None:
    token = "current-session-token"
    user = User(id=uuid.uuid4(), phone="+79990000000", display_name="Пользователь")
    session = Session(
        id=uuid.uuid4(), user_id=user.id, token_hash=hash_token(token),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db = AsyncMock()
    db.scalar.return_value = session

    with pytest.raises(HTTPException) as error:
        await revoke_session(session.id, user, token, db)

    assert getattr(error.value, "status_code", None) == 409
    assert error.value.detail["code"] == "use_logout_for_current_session"
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_foreign_session_is_hidden() -> None:
    user = User(id=uuid.uuid4(), phone="+79990000000", display_name="Пользователь")
    db = AsyncMock()
    db.scalar.return_value = None

    with pytest.raises(HTTPException) as error:
        await revoke_session(uuid.uuid4(), user, "token", db)

    assert getattr(error.value, "status_code", None) == 404
    assert error.value.detail["code"] == "session_not_found"
