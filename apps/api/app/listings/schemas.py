import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class AttributeResponse(BaseModel):
    key: str
    label: str
    value_type: str
    is_required: bool
    options: list[str] | None
    model_config = {"from_attributes": True}


class CategoryResponse(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    attributes: list[AttributeResponse] = []


class ListingCreate(BaseModel):
    category_id: uuid.UUID
    title: str = Field(min_length=3, max_length=140)
    description: str = Field(default="", max_length=10_000)
    price: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    city: str = Field(min_length=2, max_length=120)
    attributes: dict[str, object] = Field(default_factory=dict)


class ListingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=140)
    description: str | None = Field(default=None, max_length=10_000)
    price: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    city: str | None = Field(default=None, min_length=2, max_length=120)
    attributes: dict[str, object] | None = None


class ListingResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    category_id: uuid.UUID
    title: str
    description: str
    price: Decimal | None
    city: str
    attributes: dict[str, object]
    status: str
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

