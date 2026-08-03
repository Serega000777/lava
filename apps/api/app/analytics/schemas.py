import uuid

from pydantic import BaseModel


class SellerListingMetrics(BaseModel):
    listing_id: uuid.UUID
    title: str
    status: str
    favorites: int
    conversations: int
    messages: int
    reviews: int


class AdminMetrics(BaseModel):
    users: int
    active_listings: int
    open_moderation_cases: int
    conversations: int
    messages: int
    reviews: int
    ai_generations: int


class QueueMetrics(BaseModel):
    pending: int
    processing: int
    failed: int
    completed: int
    oldest_pending_seconds: int | None
    worker_healthy: bool
    heartbeat_age_seconds: int | None
