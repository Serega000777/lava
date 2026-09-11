import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ComplaintReason = Literal[
    "fraud",
    "prohibited_item",
    "duplicate",
    "misleading_content",
    "wrong_category",
    "other",
]


class ComplaintCreate(BaseModel):
    client_request_id: uuid.UUID
    reason_code: ComplaintReason
    details: str = Field(default="", max_length=2000)


class ComplaintResponse(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    reason_code: str
    details: str
    status: str
    resolution_code: str | None
    created_at: datetime
    resolved_at: datetime | None
    model_config = {"from_attributes": True}


class ComplaintCoordinationSignal(BaseModel):
    detected: bool
    window_hours: int
    reporter_count: int
    dominant_reason_code: str | None
    dominant_reason_count: int
    new_account_reporter_count: int
    indicators: list[str]


class ModerationComplaintResponse(ComplaintResponse):
    coordination_signal: ComplaintCoordinationSignal


class ComplaintDecision(BaseModel):
    decision: Literal["resolved", "dismissed"]
    resolution_code: Literal[
        "listing_restricted",
        "user_warned",
        "duplicate_report",
        "insufficient_evidence",
        "no_violation",
    ]
    comment: str = Field(default="", max_length=2000)


class AppealCreate(BaseModel):
    case_id: uuid.UUID
    reason: str = Field(min_length=20, max_length=4000)


class AppealResponse(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    appellant_id: uuid.UUID
    reason: str
    status: str
    resolution_comment: str
    created_at: datetime
    resolved_at: datetime | None
    model_config = {"from_attributes": True}


class AppealDecision(BaseModel):
    decision: Literal["upheld", "overturned"]
    comment: str = Field(min_length=10, max_length=4000)
