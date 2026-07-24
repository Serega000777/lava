from datetime import UTC, datetime

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import current_user, get_db
from app.auth.schemas import (
    AuthResponse, OtpRequest, OtpRequestResponse, OtpVerifyRequest,
    PasswordLoginRequest, PasswordRegisterRequest, ProfileUpdateRequest, UserResponse,
)
from app.auth.security import hash_token
from app.auth.service import (
    authenticate_password, create_session, register_password, request_otp, verify_otp,
)
from app.config import settings
from app.models import Session, User

router = APIRouter()
COOKIE_NAME = "lava_session"


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME, token, max_age=settings.session_ttl_hours * 3600,
        httponly=True, secure=settings.app_env == "production", samesite="lax", path="/",
    )


@router.post("/auth/register/password", response_model=AuthResponse, status_code=201)
async def password_register(
    data: PasswordRegisterRequest, response: Response, db: AsyncSession = Depends(get_db)
) -> AuthResponse:
    if not settings.password_login_enabled:
        raise HTTPException(404, detail={"code": "feature_disabled"})
    user = await register_password(db, data)
    set_session_cookie(response, await create_session(db, user))
    return AuthResponse(user=UserResponse.model_validate(user))


@router.post("/auth/login/password", response_model=AuthResponse)
async def password_login(
    data: PasswordLoginRequest, response: Response, db: AsyncSession = Depends(get_db)
) -> AuthResponse:
    if not settings.password_login_enabled:
        raise HTTPException(404, detail={"code": "feature_disabled"})
    user = await authenticate_password(db, data.phone, data.password)
    set_session_cookie(response, await create_session(db, user))
    return AuthResponse(user=UserResponse.model_validate(user))


@router.post("/auth/otp/request", response_model=OtpRequestResponse)
async def otp_request(data: OtpRequest) -> OtpRequestResponse:
    redis = Redis.from_url(settings.redis_url)
    try:
        code = await request_otp(redis, data.phone)
    finally:
        await redis.aclose()
    return OtpRequestResponse(dev_code=code)


@router.post("/auth/otp/verify", response_model=AuthResponse)
async def otp_verify(
    data: OtpVerifyRequest, response: Response, db: AsyncSession = Depends(get_db)
) -> AuthResponse:
    redis = Redis.from_url(settings.redis_url)
    try:
        valid = await verify_otp(redis, data.phone, data.code)
    finally:
        await redis.aclose()
    if not valid:
        raise HTTPException(401, detail={"code": "invalid_otp", "message": "Неверный код"})
    user = await db.scalar(select(User).where(User.phone == data.phone))
    if not user:
        user = User(phone=data.phone, display_name=data.display_name)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    set_session_cookie(response, await create_session(db, user))
    return AuthResponse(user=UserResponse.model_validate(user))


@router.post("/auth/logout", status_code=204)
async def logout(
    response: Response, lava_session: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> None:
    if lava_session:
        stored = await db.scalar(select(Session).where(Session.token_hash == hash_token(lava_session)))
        if stored:
            stored.revoked_at = datetime.now(UTC)
            await db.commit()
    response.delete_cookie(COOKIE_NAME, path="/")


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(current_user)) -> User:
    return user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: ProfileUpdateRequest, user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    user.display_name = data.display_name
    await db.commit()
    await db.refresh(user)
    return user

