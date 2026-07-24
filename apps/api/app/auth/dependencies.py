from datetime import UTC, datetime
from collections.abc import AsyncIterator

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_token
from app.db import session_factory
from app.models import Session, User


async def get_db() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


async def current_user(
    lava_session: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not lava_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "not_authenticated"})
    result = await db.execute(
        select(User).join(Session).where(
            Session.token_hash == hash_token(lava_session),
            Session.revoked_at.is_(None),
            Session.expires_at > datetime.now(UTC),
            User.is_active.is_(True),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "invalid_session"})
    return user

