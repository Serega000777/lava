import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class VerificationUpdate(BaseModel):
    level: int = Field(ge=0, le=4)
    reason_code: str = Field(pattern=r"^[a-z][a-z0-9_]{2,63}$")


class PublicTrustProfile(BaseModel):
    id: uuid.UUID
    display_name: str
    role: str
    verification_level: int
    trust_badge: str
    created_at: datetime


class VerificationDecisionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    previous_level: int
    new_level: int
    source: str
    reason_code: str
    created_at: datetime
    model_config = {"from_attributes": True}
