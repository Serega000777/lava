import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import current_user, get_db, require_permission
from app.config import settings
from app.message_reports.abuse import message_report_rate_limited
from app.message_reports.schemas import (
    MessageReportCreate,
    MessageReportDecision,
    MessageReportResponse,
    ModerationMessageReportResponse,
)
from app.message_reports.service import (
    create_message_report,
    decide_message_report,
    list_message_reports,
)
from app.models import MessageReport, User

router = APIRouter(tags=["message-reports"])


@router.post("/messages/{message_id}/reports", response_model=MessageReportResponse, status_code=201)
async def report_message(
    message_id: uuid.UUID,
    data: MessageReportCreate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageReport:
    redis = Redis.from_url(settings.redis_url)
    try:
        limited = await message_report_rate_limited(
            redis, user.id, message_id, data.client_request_id
        )
    except RedisError as error:
        raise HTTPException(503, detail={"code": "security_dependency_unavailable"}) from error
    finally:
        await redis.aclose()
    if limited:
        raise HTTPException(
            429,
            detail={"code": "message_report_rate_limited"},
            headers={"Retry-After": str(settings.complaint_rate_window_seconds)},
        )
    return await create_message_report(db, message_id, user.id, data)


@router.get("/moderation/message-reports", response_model=list[ModerationMessageReportResponse])
async def moderation_message_reports(
    status: str = Query(default="open", pattern="^(open|resolved|dismissed)$"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
    _: User = Depends(require_permission("moderation:read")),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, object]]:
    return await list_message_reports(db, status, limit, offset)


@router.post(
    "/moderation/message-reports/{report_id}/decision",
    response_model=MessageReportResponse,
)
async def message_report_decision(
    report_id: uuid.UUID,
    data: MessageReportDecision,
    user: User = Depends(require_permission("moderation:decide")),
    db: AsyncSession = Depends(get_db),
) -> MessageReport:
    return await decide_message_report(db, report_id, user.id, data)
