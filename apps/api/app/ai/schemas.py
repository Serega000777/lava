import uuid
from datetime import datetime

from pydantic import BaseModel


class GenerationRequest(BaseModel):
    client_request_id: uuid.UUID


class GenerationResponse(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    status: str
    provider: str
    model: str
    prompt_version: str
    output: dict[str, object] | None
    credit_cost: int
    created_at: datetime
    accepted_at: datetime | None
    model_config = {"from_attributes": True}


class CreditBalanceResponse(BaseModel):
    balance: int
