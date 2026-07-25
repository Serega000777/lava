import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Listing, ModerationCase, ModerationDecision
from app.moderation.schemas import DecisionRequest

LISTING_STATUS = {
    "approved": "active",
    "rejected": "rejected",
    "changes_requested": "draft",
}


async def locked_case(db: AsyncSession, case_id: uuid.UUID) -> ModerationCase:
    case = await db.scalar(
        select(ModerationCase).where(ModerationCase.id == case_id).with_for_update()
    )
    if not case:
        raise HTTPException(404, detail={"code": "moderation_case_not_found"})
    return case


async def claim_case(
    db: AsyncSession, case_id: uuid.UUID, moderator_id: uuid.UUID
) -> ModerationCase:
    case = await locked_case(db, case_id)
    if case.status != "open":
        raise HTTPException(409, detail={"code": "case_already_decided"})
    if case.assigned_to not in (None, moderator_id):
        raise HTTPException(409, detail={"code": "case_already_claimed"})
    case.assigned_to = moderator_id
    await db.commit()
    await db.refresh(case)
    return case


async def decide_case(
    db: AsyncSession,
    case_id: uuid.UUID,
    moderator_id: uuid.UUID,
    data: DecisionRequest,
) -> tuple[ModerationCase, Listing]:
    case = await locked_case(db, case_id)
    if case.status != "open":
        raise HTTPException(409, detail={"code": "case_already_decided"})
    if case.assigned_to not in (None, moderator_id):
        raise HTTPException(409, detail={"code": "case_claimed_by_another_moderator"})
    listing = await db.get(Listing, case.listing_id)
    if not listing or listing.status != "pending_moderation":
        raise HTTPException(409, detail={"code": "listing_not_pending"})
    case.assigned_to = moderator_id
    case.status = data.decision
    case.decided_at = datetime.now(UTC)
    listing.status = LISTING_STATUS[data.decision]
    db.add(ModerationDecision(
        case_id=case.id,
        moderator_id=moderator_id,
        decision=data.decision,
        reason_code=data.reason_code,
        comment=data.comment,
    ))
    await db.commit()
    await db.refresh(case)
    await db.refresh(listing)
    return case, listing

