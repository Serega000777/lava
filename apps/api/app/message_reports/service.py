import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.message_reports.schemas import MessageReportCreate, MessageReportDecision
from app.models import Conversation, Message, MessageReport


def report_payload_matches(report: MessageReport, message_id: uuid.UUID, data: MessageReportCreate) -> bool:
    return (
        report.message_id == message_id
        and report.reason_code == data.reason_code
        and report.details == data.details
    )


async def create_message_report(
    db: AsyncSession, message_id: uuid.UUID, reporter_id: uuid.UUID, data: MessageReportCreate
) -> MessageReport:
    existing = await db.scalar(
        select(MessageReport).where(
            MessageReport.reporter_id == reporter_id,
            MessageReport.client_request_id == data.client_request_id,
        )
    )
    if existing:
        if not report_payload_matches(existing, message_id, data):
            raise HTTPException(409, detail={"code": "client_request_payload_changed"})
        return existing

    row = (
        await db.execute(
            select(Message, Conversation)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Message.id == message_id,
                (Conversation.buyer_id == reporter_id) | (Conversation.seller_id == reporter_id),
            )
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(404, detail={"code": "message_not_found"})
    message, _conversation = row
    if message.sender_id == reporter_id:
        raise HTTPException(409, detail={"code": "cannot_report_own_message"})

    report = MessageReport(
        id=uuid.uuid4(),
        message_id=message.id,
        reporter_id=reporter_id,
        reported_user_id=message.sender_id,
        client_request_id=data.client_request_id,
        reason_code=data.reason_code,
        details=data.details,
    )
    db.add(report)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        existing = await db.scalar(
            select(MessageReport).where(
                MessageReport.reporter_id == reporter_id,
                MessageReport.client_request_id == data.client_request_id,
            )
        )
        if existing:
            if not report_payload_matches(existing, message_id, data):
                raise HTTPException(
                    409, detail={"code": "client_request_payload_changed"}
                ) from error
            return existing
        existing = await db.scalar(
            select(MessageReport).where(
                MessageReport.reporter_id == reporter_id,
                MessageReport.message_id == message_id,
            )
        )
        if existing:
            return existing
        raise HTTPException(409, detail={"code": "message_report_conflict"}) from error
    await db.refresh(report)
    return report


async def list_message_reports(
    db: AsyncSession, status: str, limit: int, offset: int
) -> list[dict[str, object]]:
    rows = (
        await db.execute(
            select(MessageReport, Message.body, Message.created_at)
            .join(Message, Message.id == MessageReport.message_id)
            .where(MessageReport.status == status)
            .order_by(MessageReport.created_at)
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return [
        {
            **{column.name: getattr(report, column.name) for column in MessageReport.__table__.columns},
            "message_body": body,
            "message_created_at": message_created_at,
        }
        for report, body, message_created_at in rows
    ]


async def decide_message_report(
    db: AsyncSession,
    report_id: uuid.UUID,
    moderator_id: uuid.UUID,
    data: MessageReportDecision,
) -> MessageReport:
    report = await db.scalar(
        select(MessageReport).where(MessageReport.id == report_id).with_for_update()
    )
    if report is None:
        raise HTTPException(404, detail={"code": "message_report_not_found"})
    if report.status != "open":
        raise HTTPException(409, detail={"code": "message_report_already_decided"})
    report.status = data.decision
    report.resolution_code = data.resolution_code
    report.resolution_comment = data.comment
    report.resolved_by = moderator_id
    report.resolved_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(report)
    return report
