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


class ReviewReplyCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)

    @field_validator("body")
    @classmethod
    def normalize_body(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("reply body cannot be blank")
        return value


class ReviewReplyResponse(BaseModel):
    id: uuid.UUID
    review_id: uuid.UUID
    author_id: uuid.UUID
    body: str
    created_at: datetime
    model_config = {"from_attributes": True}


class PublicReviewReplyResponse(BaseModel):
    responder_name: str
    body: str
    created_at: datetime


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
    reply: PublicReviewReplyResponse | None


class ReputationResponse(BaseModel):
    user_id: uuid.UUID
    average_rating: Decimal | None
    review_count: int
