import uuid
from datetime import datetime

from pydantic import BaseModel, computed_field


class MediaResponse(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    content_type: str
    size_bytes: int
    width: int
    height: int
    position: int
    created_at: datetime

    @computed_field
    @property
    def url(self) -> str:
        return f"/media/{self.id}"

    model_config = {"from_attributes": True}
