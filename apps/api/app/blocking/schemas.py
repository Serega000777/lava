import uuid
from datetime import datetime

from pydantic import BaseModel


class BlockedUserResponse(BaseModel):
    user_id: uuid.UUID
    display_name: str
    created_at: datetime
