import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_db, require_permission
from app.models import ModerationCase, User
from app.moderation.schemas import DecisionRequest, DecisionResponse, ModerationCaseResponse
from app.moderation.service import claim_case, decide_case

router = APIRouter(prefix="/moderation", tags=["moderation"])


@router.get("/cases", response_model=list[ModerationCaseResponse])
async def list_cases(
    case_status: str = Query(default="open", alias="status"),
    _: User = Depends(require_permission("moderation:read")),
    db: AsyncSession = Depends(get_db),
) -> list[ModerationCase]:
    return list((await db.scalars(
        select(ModerationCase)
        .where(ModerationCase.status == case_status)
        .order_by(ModerationCase.created_at)
    )).all())


@router.post("/cases/{case_id}/claim", response_model=ModerationCaseResponse)
async def claim(
    case_id: uuid.UUID,
    user: User = Depends(require_permission("moderation:decide")),
    db: AsyncSession = Depends(get_db),
) -> ModerationCase:
    return await claim_case(db, case_id, user.id)


@router.post("/cases/{case_id}/decision", response_model=DecisionResponse)
async def decision(
    case_id: uuid.UUID,
    data: DecisionRequest,
    user: User = Depends(require_permission("moderation:decide")),
    db: AsyncSession = Depends(get_db),
) -> DecisionResponse:
    case, listing = await decide_case(db, case_id, user.id, data)
    return DecisionResponse(
        case=ModerationCaseResponse.model_validate(case),
        listing_status=listing.status,
    )

