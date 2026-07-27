import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

class SearchQuery(BaseModel):
    q: str = Field(default="", max_length=200)
    category_id: uuid.UUID | None = None
    city: str | None = Field(default=None, max_length=120)
    price_min: Decimal | None = Field(default=None, ge=0)
    price_max: Decimal | None = Field(default=None, ge=0)
    sort: str = Field(default="relevance", pattern=r"^(relevance|newest|price_asc|price_desc)$")
    limit: int = Field(default=24, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10_000)

    @model_validator(mode="after")
    def validate_price_range(self) -> "SearchQuery":
        if self.price_min is not None and self.price_max is not None:
            if self.price_min > self.price_max:
                raise ValueError("price_min must not exceed price_max")
        return self


class PublicListingResponse(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    title: str
    description: str
    price: Decimal | None
    city: str
    attributes: dict[str, object]
    ai_generated_fields: list[str]
    created_at: datetime
    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    items: list[PublicListingResponse]
    total: int
    limit: int
    offset: int
