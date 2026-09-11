from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.abuse import (
    auth_identity,
    clear_password_failures,
    password_failure_count,
    password_retry_after,
    record_password_failure,
)
from app.auth.schemas import PasswordRegisterRequest
from app.auth.security import (
    hash_password,
    hash_token,
    new_otp_code,
    new_session_token,
    verify_password,
)
from app.config import settings
from app.models import PasswordCredential, Session, User

DUMMY_PASSWORD_HASH = hash_password("Lava timing equalization value 2026")


async def register_password(db: AsyncSession, data: PasswordRegisterRequest) -> User:
    if await db.scalar(select(User).where(User.phone == data.phone)):
        raise HTTPException(
            409,
            detail={"code": "phone_exists", "message": "Телефон уже зарегистрирован"},
        )
    user = User(phone=data.phone, display_name=data.display_name)
    db.add(user)
    await db.flush()
    db.add(PasswordCredential(user_id=user.id, password_hash=hash_password(data.password)))
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_password(db: AsyncSession, phone: str, password: str) -> User:
    result = await db.execute(
        select(User, PasswordCredential)
        .join(PasswordCredential, PasswordCredential.user_id == User.id)
        .where(User.phone == phone, User.is_active.is_(True))
    )
    row = result.one_or_none()
    password_hash = row.PasswordCredential.password_hash if row else DUMMY_PASSWORD_HASH
    password_is_valid = verify_password(password_hash, password)
    if not row or not password_is_valid:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_credentials", "message": "Неверный телефон или пароль"},
        )
    return row.User


async def authenticate_password_with_delay(
    db: AsyncSession,
    redis: Redis,
    phone: str,
    password: str,
) -> User:
    retry_after = await password_retry_after(redis, phone)
    if retry_after:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "account_login_delayed", "message": "Повторите попытку позже"},
            headers={"Retry-After": str(retry_after)},
        )
    observed_attempts = await password_failure_count(redis, phone)
    try:
        user = await authenticate_password(db, phone, password)
    except HTTPException as error:
        if error.status_code != status.HTTP_401_UNAUTHORIZED:
            raise
        retry_after = await record_password_failure(redis, phone)
        if retry_after:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"code": "account_login_delayed", "message": "Повторите попытку позже"},
                headers={"Retry-After": str(retry_after)},
            ) from error
        raise
    await clear_password_failures(redis, phone, observed_attempts)
    return user


async def create_session(db: AsyncSession, user: User) -> str:
    token = new_session_token()
    db.add(
        Session(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(UTC) + timedelta(hours=settings.session_ttl_hours),
        )
    )
    await db.commit()
    return token


def otp_key(purpose: str, phone: str) -> str:
    if purpose not in {"login", "recovery"}:
        raise ValueError("unsupported OTP purpose")
    return f"auth:otp:{purpose}:{auth_identity(phone)}"


async def request_otp(redis: Redis, phone: str, purpose: str = "login") -> str | None:
    if not settings.local_otp_enabled and not settings.sms_otp_enabled:
        raise HTTPException(503, detail={"code": "otp_unavailable"})
    key = otp_key(purpose, phone)
    if await redis.get(f"{key}:rate"):
        raise HTTPException(
            429,
            detail={"code": "otp_rate_limited", "message": "Повторите запрос позже"},
        )
    code = new_otp_code()
    await redis.delete(f"{key}:attempts")
    await redis.setex(key, 300, hash_token(code))
    await redis.setex(f"{key}:rate", 60, "1")
    return code if settings.app_env == "development" and settings.local_otp_enabled else None


async def verify_otp(
    redis: Redis,
    phone: str,
    code: str,
    purpose: str = "login",
) -> bool:
    key = otp_key(purpose, phone)
    attempts_key = f"{key}:attempts"
    attempts = await redis.incr(attempts_key)
    if attempts == 1:
        await redis.expire(attempts_key, 300)
    if attempts > settings.otp_max_attempts:
        await redis.delete(key)
        return False
    expected = await redis.get(key)
    if not expected or expected.decode() != hash_token(code):
        return False
    await redis.delete(key, attempts_key)
    return True


async def reset_password_and_revoke_sessions(
    db: AsyncSession,
    phone: str,
    new_password: str,
) -> User:
    user = await db.scalar(select(User).where(User.phone == phone).with_for_update())
    if not user or not user.is_active:
        raise HTTPException(401, detail={"code": "invalid_recovery"})
    credential = await db.get(PasswordCredential, user.id)
    if credential:
        credential.password_hash = hash_password(new_password)
    else:
        db.add(
            PasswordCredential(
                user_id=user.id,
                password_hash=hash_password(new_password),
            )
        )
    await db.execute(
        update(Session)
        .where(Session.user_id == user.id, Session.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await db.commit()
    await db.refresh(user)
    return user
