from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import PasswordRegisterRequest
from app.auth.security import hash_password, hash_token, new_otp_code, new_session_token, verify_password
from app.config import settings
from app.models import PasswordCredential, Session, User


async def register_password(db: AsyncSession, data: PasswordRegisterRequest) -> User:
    if await db.scalar(select(User).where(User.phone == data.phone)):
        raise HTTPException(409, detail={"code": "phone_exists", "message": "Телефон уже зарегистрирован"})
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
    if not row or not verify_password(row.PasswordCredential.password_hash, password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_credentials", "message": "Неверный телефон или пароль"},
        )
    return row.User


async def create_session(db: AsyncSession, user: User) -> str:
    token = new_session_token()
    db.add(Session(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=datetime.now(UTC) + timedelta(hours=settings.session_ttl_hours),
    ))
    await db.commit()
    return token


async def request_otp(redis: Redis, phone: str) -> str | None:
    if not settings.local_otp_enabled and not settings.sms_otp_enabled:
        raise HTTPException(503, detail={"code": "otp_unavailable"})
    if await redis.get(f"auth:otp:rate:{phone}"):
        raise HTTPException(429, detail={"code": "otp_rate_limited", "message": "Повторите запрос позже"})
    code = new_otp_code()
    await redis.setex(f"auth:otp:{phone}", 300, hash_token(code))
    await redis.setex(f"auth:otp:rate:{phone}", 60, "1")
    return code if settings.app_env == "development" and settings.local_otp_enabled else None


async def verify_otp(redis: Redis, phone: str, code: str) -> bool:
    key = f"auth:otp:{phone}"
    expected = await redis.get(key)
    if not expected or expected.decode() != hash_token(code):
        return False
    await redis.delete(key)
    return True

