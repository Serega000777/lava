import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ConversationCreate(BaseModel):
    listing_id: uuid.UUID


class ConversationResponse(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    buyer_id: uuid.UUID
    seller_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class ConversationSummary(ConversationResponse):
    listing_title: str
    counterpart_id: uuid.UUID
    counterpart_name: str
    is_muted: bool


class MessageCreate(BaseModel):
    client_message_id: uuid.UUID
    body: str = Field(min_length=1, max_length=4000)

    @field_validator("body")
    @classmethod
    def reject_blank_body(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message body cannot be blank")
        return value


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    client_message_id: uuid.UUID
    body: str
    created_at: datetime
    read_at: datetime | None
    model_config = {"from_attributes": True}


class ReadReceiptResponse(BaseModel):
    read_count: int
    read_at: datetime | None


class NotificationResponse(BaseModel):
    id: uuid.UUID
    kind: str
    conversation_id: uuid.UUID
    read_at: datetime | None
    created_at: datetime
    model_config = {"from_attributes": True}
