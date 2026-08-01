import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

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
from app.models import (
    Complaint,
    Listing,
    ModerationAppeal,
    ModerationCase,
    ModerationDecision,
    User,
)

COORDINATION_WINDOW_HOURS = 24
NEW_ACCOUNT_MAX_AGE_DAYS = 7
MIN_COORDINATED_REPORTERS = 3


@dataclass(frozen=True)
class ComplaintSignalInput:
    reporter_id: uuid.UUID
    reason_code: str
    account_created_at: datetime


def assess_complaint_coordination(
    reports: list[ComplaintSignalInput],
    *,
    now: datetime,
) -> dict[str, object]:
    unique_reports: dict[uuid.UUID, ComplaintSignalInput] = {}
    for report in reports:
        unique_reports.setdefault(report.reporter_id, report)
    reporter_count = len(unique_reports)
    reasons = Counter(report.reason_code for report in unique_reports.values())
    dominant_reason_code: str | None = None
    dominant_reason_count = 0
    if reasons:
        dominant_reason_code, dominant_reason_count = reasons.most_common(1)[0]
    new_account_cutoff = now - timedelta(days=NEW_ACCOUNT_MAX_AGE_DAYS)
    new_account_count = sum(
        report.account_created_at >= new_account_cutoff for report in unique_reports.values()
    )
    indicators: list[str] = []
    if reporter_count >= MIN_COORDINATED_REPORTERS:
        indicators.append("reporter_burst")
    if (
        reporter_count >= MIN_COORDINATED_REPORTERS
        and dominant_reason_count / reporter_count >= 0.8
    ):
        indicators.append("reason_concentration")
    if new_account_count >= MIN_COORDINATED_REPORTERS:
        indicators.append("new_account_cluster")
    return {
        "detected": len(indicators) >= 2,
        "window_hours": COORDINATION_WINDOW_HOURS,
        "reporter_count": reporter_count,
        "dominant_reason_code": dominant_reason_code,
        "dominant_reason_count": dominant_reason_count,
        "new_account_reporter_count": new_account_count,
        "indicators": indicators,
    }


async def list_complaints_for_moderation(
    db: AsyncSession,
    *,
    complaint_status: str,
    limit: int,
    offset: int,
) -> list[dict[str, object]]:
    complaints = list(
        (
            await db.scalars(
                select(Complaint)
                .where(Complaint.status == complaint_status)
                .order_by(Complaint.created_at, Complaint.id)
                .limit(limit)
                .offset(offset)
            )
        ).all()
    )
    if not complaints:
        return []

    now = datetime.now(UTC)
    rows = (
        await db.execute(
            select(Complaint, User.created_at)
            .join(User, User.id == Complaint.reporter_id)
            .where(
                Complaint.listing_id.in_({item.listing_id for item in complaints}),
                Complaint.created_at >= now - timedelta(hours=COORDINATION_WINDOW_HOURS),
            )
            .order_by(Complaint.created_at, Complaint.id)
        )
    ).all()
    reports_by_listing: dict[uuid.UUID, list[ComplaintSignalInput]] = {}
    for complaint, account_created_at in rows:
        reports_by_listing.setdefault(complaint.listing_id, []).append(
            ComplaintSignalInput(
                reporter_id=complaint.reporter_id,
                reason_code=complaint.reason_code,
                account_created_at=account_created_at,
            )
        )
    return [
        {
            "id": item.id,
            "listing_id": item.listing_id,
            "reason_code": item.reason_code,
            "details": item.details,
            "status": item.status,
            "resolution_code": item.resolution_code,
            "created_at": item.created_at,
            "resolved_at": item.resolved_at,
            "coordination_signal": assess_complaint_coordination(
                reports_by_listing.get(item.listing_id, []), now=now
            ),
        }
        for item in complaints
    ]

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
