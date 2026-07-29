import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import current_user, get_db, require_permission
from app.complaints.schemas import (
    AppealCreate,
    AppealDecision,
    AppealResponse,
    ComplaintCreate,
    ComplaintDecision,
    ComplaintResponse,
)
from app.complaints.service import (
    create_appeal,
    create_complaint,
    decide_appeal,
    decide_complaint,
)
from app.models import Complaint, ModerationAppeal, User

router = APIRouter(tags=["complaints"])


@router.post(
    "/listings/{listing_id}/complaints",
    response_model=ComplaintResponse,
    status_code=201,
)
async def report_listing(
    listing_id: uuid.UUID,
    data: ComplaintCreate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> Complaint:
    return await create_complaint(db, listing_id, user.id, data)


@router.get("/complaints/mine", response_model=list[ComplaintResponse])
async def my_complaints(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Complaint]:
    return list(
        (
            await db.scalars(
                select(Complaint)
                .where(Complaint.reporter_id == user.id)
                .order_by(Complaint.created_at.desc())
            )
        ).all()
    )


@router.get("/moderation/complaints", response_model=list[ComplaintResponse])
async def moderation_complaints(
    complaint_status: str = Query(default="open", alias="status", pattern="^(open|resolved|dismissed)$"),
    _: User = Depends(require_permission("moderation:read")),
    db: AsyncSession = Depends(get_db),
) -> list[Complaint]:
    return list(
        (
            await db.scalars(
                select(Complaint)
                .where(Complaint.status == complaint_status)
                .order_by(Complaint.created_at)
            )
        ).all()
    )


@router.post(
    "/moderation/complaints/{complaint_id}/decision",
    response_model=ComplaintResponse,
)
async def complaint_decision(
    complaint_id: uuid.UUID,
    data: ComplaintDecision,
    user: User = Depends(require_permission("moderation:decide")),
    db: AsyncSession = Depends(get_db),
) -> Complaint:
    return await decide_complaint(db, complaint_id, user.id, data)


@router.post("/moderation/appeals", response_model=AppealResponse, status_code=201)
async def submit_appeal(
    data: AppealCreate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> ModerationAppeal:
    return await create_appeal(db, user.id, data)


@router.get("/moderation/appeals", response_model=list[AppealResponse])
async def list_appeals(
    appeal_status: str = Query(default="open", alias="status", pattern="^(open|upheld|overturned)$"),
    _: User = Depends(require_permission("moderation:read")),
    db: AsyncSession = Depends(get_db),
) -> list[ModerationAppeal]:
    return list(
        (
            await db.scalars(
                select(ModerationAppeal)
                .where(ModerationAppeal.status == appeal_status)
                .order_by(ModerationAppeal.created_at)
            )
        ).all()
    )


@router.post(
    "/moderation/appeals/{appeal_id}/decision",
    response_model=AppealResponse,
)
async def appeal_decision(
    appeal_id: uuid.UUID,
    data: AppealDecision,
    user: User = Depends(require_permission("moderation:decide")),
    db: AsyncSession = Depends(get_db),
) -> ModerationAppeal:
    return await decide_appeal(db, appeal_id, user.id, data)
