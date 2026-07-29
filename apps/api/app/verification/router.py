import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_db, require_permission
from app.models import User
from app.verification.schemas import (
    PublicTrustProfile,
    VerificationDecisionResponse,
    VerificationUpdate,
)
from app.verification.service import set_verification_level, trust_badge

router = APIRouter(tags=["verification"])


@router.get("/users/{user_id}/profile", response_model=PublicTrustProfile)
async def public_profile(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PublicTrustProfile:
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        from fastapi import HTTPException
        raise HTTPException(404, detail={"code": "user_not_found"})
    return PublicTrustProfile(
        id=user.id,
        display_name=user.display_name,
        role=user.role,
        verification_level=user.verification_level,
        trust_badge=trust_badge(user.verification_level, user.role),
        created_at=user.created_at,
    )


@router.post(
    "/admin/users/{user_id}/verification",
    response_model=VerificationDecisionResponse,
)
async def update_verification(
    user_id: uuid.UUID,
    data: VerificationUpdate,
    admin: User = Depends(require_permission("verification:manage")),
    db: AsyncSession = Depends(get_db),
) -> VerificationDecisionResponse:
    return await set_verification_level(db, user_id, admin.id, data.level, data.reason_code)
