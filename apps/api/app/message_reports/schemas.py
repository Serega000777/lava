import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MessageReportCreate(BaseModel):
    client_request_id: uuid.UUID
    reason_code: Literal["spam", "fraud", "harassment", "prohibited_content", "other"]
    details: str = Field(default="", max_length=2000)


class MessageReportResponse(BaseModel):
    id: uuid.UUID
    message_id: uuid.UUID
    reason_code: str
    details: str
    status: str
    resolution_code: str | None
    created_at: datetime
    resolved_at: datetime | None
    model_config = {"from_attributes": True}


class ModerationMessageReportResponse(MessageReportResponse):
    reporter_id: uuid.UUID
    reported_user_id: uuid.UUID
    message_body: str
    message_created_at: datetime


class MessageReportDecision(BaseModel):
    decision: Literal["resolved", "dismissed"]
    resolution_code: Literal["user_warned", "escalated", "duplicate_report", "no_violation"]
    comment: str = Field(default="", max_length=2000)
