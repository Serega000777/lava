import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.complaints.schemas import (
    AppealCreate,
    AppealDecision,
    ComplaintCreate,
    ComplaintDecision,
)
from app.models import Complaint, Listing, ModerationAppeal, ModerationCase, ModerationDecision

COMPLAINT_RESOLUTION_CODES = {
    "resolved": frozenset({"listing_restricted", "user_warned"}),
    "dismissed": frozenset({"duplicate_report", "insufficient_evidence", "no_violation"}),
}


def complaint_payload_matches(
    complaint: Complaint,
    listing_id: uuid.UUID,
    data: ComplaintCreate,
) -> bool:
    return (
        complaint.listing_id == listing_id
        and complaint.reason_code == data.reason_code
        and complaint.details == data.details
    )


async def create_complaint(
    db: AsyncSession,
    listing_id: uuid.UUID,
    reporter_id: uuid.UUID,
    data: ComplaintCreate,
) -> Complaint:
    existing = await db.scalar(
        select(Complaint).where(
            Complaint.reporter_id == reporter_id,
            Complaint.client_request_id == data.client_request_id,
        )
    )
    if existing:
        if not complaint_payload_matches(existing, listing_id, data):
            raise HTTPException(409, detail={"code": "idempotency_key_reused"})
        return existing
    listing = await db.scalar(
        select(Listing).where(Listing.id == listing_id, Listing.status == "active")
    )
    if not listing:
        raise HTTPException(404, detail={"code": "listing_not_found"})
    if listing.owner_id == reporter_id:
        raise HTTPException(409, detail={"code": "self_complaint_not_allowed"})
    complaint = Complaint(
        listing_id=listing.id,
        listing_owner_id=listing.owner_id,
        reporter_id=reporter_id,
        client_request_id=data.client_request_id,
        reason_code=data.reason_code,
        details=data.details,
    )
    db.add(complaint)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await db.scalar(
            select(Complaint).where(
                Complaint.reporter_id == reporter_id,
                Complaint.client_request_id == data.client_request_id,
            )
        )
        if not existing or not complaint_payload_matches(existing, listing_id, data):
            raise
        return existing
    await db.refresh(complaint)
    return complaint


async def decide_complaint(
    db: AsyncSession,
    complaint_id: uuid.UUID,
    moderator_id: uuid.UUID,
    data: ComplaintDecision,
) -> Complaint:
    if data.resolution_code not in COMPLAINT_RESOLUTION_CODES[data.decision]:
        raise HTTPException(422, detail={"code": "invalid_resolution_code"})
    complaint = await db.scalar(
        select(Complaint).where(Complaint.id == complaint_id).with_for_update()
    )
    if not complaint:
        raise HTTPException(404, detail={"code": "complaint_not_found"})
    if complaint.status != "open":
        raise HTTPException(409, detail={"code": "complaint_already_decided"})
    complaint.status = data.decision
    complaint.resolution_code = data.resolution_code
    complaint.resolution_comment = data.comment
    complaint.resolved_by = moderator_id
    complaint.resolved_at = datetime.now(UTC)
    if data.decision == "resolved" and data.resolution_code == "listing_restricted":
        listing = await db.get(Listing, complaint.listing_id)
        if not listing:
            raise HTTPException(409, detail={"code": "complaint_subject_not_found"})
        listing.status = "archived"
    await db.commit()
    await db.refresh(complaint)
    return complaint


async def create_appeal(
    db: AsyncSession,
    appellant_id: uuid.UUID,
    data: AppealCreate,
) -> ModerationAppeal:
    case = await db.scalar(
        select(ModerationCase)
        .join(Listing, Listing.id == ModerationCase.listing_id)
        .where(ModerationCase.id == data.case_id, Listing.owner_id == appellant_id)
    )
    if not case:
        raise HTTPException(404, detail={"code": "moderation_case_not_found"})
    if case.status not in {"rejected", "changes_requested"}:
        raise HTTPException(409, detail={"code": "case_not_appealable"})
    existing = await db.scalar(
        select(ModerationAppeal).where(ModerationAppeal.case_id == case.id)
    )
    if existing:
        if existing.appellant_id != appellant_id or existing.reason != data.reason:
            raise HTTPException(409, detail={"code": "appeal_already_submitted"})
        return existing
    appeal = ModerationAppeal(
        case_id=case.id,
        appellant_id=appellant_id,
        reason=data.reason,
    )
    db.add(appeal)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await db.scalar(
            select(ModerationAppeal).where(ModerationAppeal.case_id == case.id)
        )
        if not existing or existing.appellant_id != appellant_id or existing.reason != data.reason:
            raise
        return existing
    await db.refresh(appeal)
    return appeal


async def decide_appeal(
    db: AsyncSession,
    appeal_id: uuid.UUID,
    moderator_id: uuid.UUID,
    data: AppealDecision,
) -> ModerationAppeal:
    appeal = await db.scalar(
        select(ModerationAppeal)
        .where(ModerationAppeal.id == appeal_id)
        .with_for_update()
    )
    if not appeal:
        raise HTTPException(404, detail={"code": "appeal_not_found"})
    if appeal.status != "open":
        raise HTTPException(409, detail={"code": "appeal_already_decided"})
    original_moderator = await db.scalar(
        select(ModerationDecision.moderator_id)
        .where(ModerationDecision.case_id == appeal.case_id)
        .order_by(ModerationDecision.created_at.desc())
        .limit(1)
    )
    if original_moderator == moderator_id:
        raise HTTPException(409, detail={"code": "independent_review_required"})
    if original_moderator is None:
        raise HTTPException(409, detail={"code": "original_decision_not_found"})
    appeal.status = data.decision
    appeal.reviewed_by = moderator_id
    appeal.resolution_comment = data.comment
    appeal.resolved_at = datetime.now(UTC)
    if data.decision == "overturned":
        original_case = await db.get(ModerationCase, appeal.case_id)
        listing = await db.get(Listing, original_case.listing_id if original_case else None)
        if not original_case or not listing:
            raise HTTPException(409, detail={"code": "appeal_subject_not_found"})
        listing.status = "pending_moderation"
        db.add(ModerationCase(listing_id=listing.id))
    await db.commit()
    await db.refresh(appeal)
    return appeal
