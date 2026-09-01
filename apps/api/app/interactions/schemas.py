import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class InteractionResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    status: Literal["awaiting_contact", "contacted", "completed"]
    my_completion_confirmed: bool
    counterpart_completion_confirmed: bool
    completed_at: datetime | None
    can_review: bool
    review_created: bool
