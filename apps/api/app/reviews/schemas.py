import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=2000)

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str) -> str:
        return value.strip()


class ReviewResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    reviewer_id: uuid.UUID
    reviewee_id: uuid.UUID
    reviewer_name: str
    rating: int
    comment: str
    created_at: datetime


class PublicReviewResponse(BaseModel):
    id: uuid.UUID
    reviewer_name: str
    rating: int
    comment: str
    created_at: datetime


class ReputationResponse(BaseModel):
    user_id: uuid.UUID
    average_rating: Decimal | None
    review_count: int
