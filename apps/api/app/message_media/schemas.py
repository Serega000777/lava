import uuid
from datetime import datetime

from pydantic import BaseModel


class MessageMediaResponse(BaseModel):
    id: uuid.UUID
    message_id: uuid.UUID
    content_type: str
    size_bytes: int
    width: int
    height: int
    position: int
    created_at: datetime
    model_config = {"from_attributes": True}
