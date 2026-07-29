import uuid
from datetime import datetime

from decimal import Decimal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'specialist', 'company', 'moderator', 'admin')"),
        CheckConstraint("verification_level BETWEEN 0 AND 4"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(24), default="user")
    verification_level: Mapped[int] = mapped_column(SmallInteger, default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PasswordCredential(Base):
    __tablename__ = "password_credentials"
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    password_hash: Mapped[str] = mapped_column(String(255))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CategoryAttribute(Base):
    __tablename__ = "category_attributes"
    __table_args__ = (
        CheckConstraint("value_type IN ('text', 'number', 'boolean', 'select')"),
        UniqueConstraint("category_id", "key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(120))
    value_type: Mapped[str] = mapped_column(String(16))
    is_required: Mapped[bool] = mapped_column(default=False)
    options: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'pending_moderation', 'active', 'rejected', 'archived')"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id"), index=True
    )
    title: Mapped[str] = mapped_column(String(140))
    description: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    city: Mapped[str] = mapped_column(String(120))
    attributes: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    ai_generated_fields: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ListingMedia(Base):
    __tablename__ = "listing_media"
    __table_args__ = (
        CheckConstraint("position BETWEEN 0 AND 9"),
        CheckConstraint("size_bytes > 0"),
        UniqueConstraint("listing_id", "position"),
        UniqueConstraint("object_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    object_key: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column()
    width: Mapped[int] = mapped_column()
    height: Mapped[int] = mapped_column()
    position: Mapped[int] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Favorite(Base):
    __tablename__ = "favorites"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("listing_id", "buyer_id"),
        CheckConstraint("buyer_id <> seller_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE")
    )
    buyer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("sender_id", "client_message_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE")
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    client_message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint("kind IN ('new_conversation', 'new_message')"),
        UniqueConstraint("user_id", "source_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(32))
    source_key: Mapped[str] = mapped_column(String(100))
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE")
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5"),
        CheckConstraint("reviewer_id <> reviewee_id"),
        UniqueConstraint("conversation_id", "reviewer_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE")
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    reviewee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    rating: Mapped[int] = mapped_column(SmallInteger)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CreditAccount(Base):
    __tablename__ = "credit_accounts"
    __table_args__ = (CheckConstraint("balance >= 0"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    balance: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CreditLedgerEntry(Base):
    __tablename__ = "credit_ledger"
    __table_args__ = (
        CheckConstraint("kind IN ('welcome_grant', 'ai_text_debit', 'ai_text_refund')"),
        CheckConstraint("amount <> 0"),
        CheckConstraint("balance_after >= 0"),
        UniqueConstraint("user_id", "kind", "reference_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(32))
    amount: Mapped[int] = mapped_column()
    balance_after: Mapped[int] = mapped_column()
    reference_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AiGeneration(Base):
    __tablename__ = "ai_generations"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'completed', 'failed', 'accepted')"),
        UniqueConstraint("user_id", "client_request_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE")
    )
    client_request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(24), default="pending")
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(64))
    prompt_version: Mapped[str] = mapped_column(String(32))
    input_snapshot: Mapped[dict[str, object]] = mapped_column(JSON)
    output: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    credit_cost: Mapped[int] = mapped_column(default=1)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ModerationCase(Base):
    __tablename__ = "moderation_cases"
    __table_args__ = (
        CheckConstraint("status IN ('open', 'approved', 'rejected', 'changes_requested')"),
        Index(
            "uq_moderation_cases_one_open_per_listing",
            "listing_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ModerationDecision(Base):
    __tablename__ = "moderation_decisions"
    __table_args__ = (
        CheckConstraint("decision IN ('approved', 'rejected', 'changes_requested')"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("moderation_cases.id", ondelete="CASCADE"), index=True
    )
    moderator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String(24))
    reason_code: Mapped[str] = mapped_column(String(64))
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
