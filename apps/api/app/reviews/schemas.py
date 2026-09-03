import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


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


class ReceivedReviewResponse(PublicReviewResponse):
    dispute_status: Literal["open", "keep", "exclude"] | None
    dispute_resolution_reason: str | None = None
    dispute_resolution_comment: str | None = None


class ReviewDisputeCreate(BaseModel):
    reason_code: Literal[
        "transaction_not_completed", "abusive", "personal_data", "fraudulent", "other"
    ]
    details: str = Field(default="", max_length=4000)

    @field_validator("details")
    @classmethod
    def normalize_details(cls, value: str) -> str:
        return value.strip()


class ReviewDisputeResponse(BaseModel):
    id: uuid.UUID
    review_id: uuid.UUID
    reason_code: str
    details: str
    created_at: datetime
    model_config = {"from_attributes": True}


class ModerationReviewDisputeResponse(ReviewDisputeResponse):
    rating: int
    review_comment: str
    reviewer_name: str
    reviewee_name: str


class ReviewDisputeDecisionCreate(BaseModel):
    outcome: Literal["keep", "exclude"]
    reason_code: Literal[
        "complies",
        "insufficient_evidence",
        "abusive",
        "personal_data",
        "fraudulent",
        "transaction_not_completed",
        "other",
    ]
    comment: str = Field(default="", max_length=4000)

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def reason_matches_outcome(self):
        keep_reasons = {"complies", "insufficient_evidence"}
        if (self.outcome == "keep") != (self.reason_code in keep_reasons):
            raise ValueError("reason code does not match decision outcome")
        return self


class ReviewDisputeDecisionResponse(BaseModel):
    id: uuid.UUID
    dispute_id: uuid.UUID
    moderator_id: uuid.UUID
    outcome: str
    reason_code: str
    comment: str
    created_at: datetime
    model_config = {"from_attributes": True}


class ReputationResponse(BaseModel):
    user_id: uuid.UUID
    average_rating: Decimal | None
    review_count: int


class ReputationSignalResponse(BaseModel):
    user_id: uuid.UUID
    display_name: str
    detected: bool
    window_hours: int
    review_count: int
    distinct_reviewer_count: int
    new_account_reviewer_count: int
    dominant_rating: int | None
    dominant_rating_count: int
    repeat_review_count: int
    indicators: list[str]
