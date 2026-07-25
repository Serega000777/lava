import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ModerationCaseResponse(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    status: str
    assigned_to: uuid.UUID | None
    created_at: datetime
    decided_at: datetime | None
    model_config = {"from_attributes": True}


class DecisionRequest(BaseModel):
    decision: str = Field(pattern=r"^(approved|rejected|changes_requested)$")
    reason_code: str = Field(min_length=2, max_length=64)
    comment: str = Field(default="", max_length=2000)


class DecisionResponse(BaseModel):
    case: ModerationCaseResponse
    listing_status: str

