import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, VerificationDecision

TRUST_BADGES = {
    0: "Новый",
    1: "Телефон подтверждён",
    2: "Личность проверена",
    3: "Расширенная проверка",
    4: "Организация проверена",
}


def trust_badge(level: int, role: str) -> str:
    if level == 4 and role == "company":
        return "Проверенная компания"
    return TRUST_BADGES.get(level, TRUST_BADGES[0])


async def set_verification_level(
    db: AsyncSession,
    user_id: uuid.UUID,
    actor_id: uuid.UUID,
    new_level: int,
    reason_code: str,
) -> VerificationDecision:
    user = await db.scalar(select(User).where(User.id == user_id).with_for_update())
    if not user:
        raise HTTPException(404, detail={"code": "user_not_found"})
    if user.verification_level == new_level:
        raise HTTPException(409, detail={"code": "verification_level_unchanged"})
    if new_level == 4 and user.role != "company":
        raise HTTPException(409, detail={"code": "organization_level_requires_company"})
    decision = VerificationDecision(
        user_id=user.id,
        actor_id=actor_id,
        source="admin_review",
        previous_level=user.verification_level,
        new_level=new_level,
        reason_code=reason_code,
    )
    user.verification_level = new_level
    db.add(decision)
    await db.commit()
    await db.refresh(decision)
    return decision
