# Data model

The first migration creates `categories(id UUID PK, slug UNIQUE, name, created_at timestamptz)`.

Migration 0003 adds data-driven `category_attributes` and owner-scoped `listings`. Listings store common searchable fields in typed columns and category-specific values in JSONB.

Aggregates include users/sessions/verifications, category attributes,
listings/media, moderation cases, favorites, conversations/messages,
interactions/reviews, complaints/appeals, notifications, transactional outbox
tasks, AI jobs/versions, immutable credit ledger entries and audit events. Foreign
keys, uniqueness constraints and partial indexes enforce invariants.

Migration 0021 makes interactions explicit. Each conversation has one interaction
with a first-contact timestamp and immutable buyer/seller completion timestamps.
Both confirmations are required for completion. Reviews reference the matching
interaction and conversation through a composite foreign key and cannot be updated.

Migration 0022 adds one optional immutable `review_replies` row per review. A
composite foreign key guarantees that the stored reply author is the reviewee;
indexes support review lookup and owner-scoped cabinet access.

Migration 0012 adds append-only `verification_decisions`. Sensitive identity
evidence is intentionally excluded from the MVP database.
Migration 0013 enforces decision immutability with a database trigger.
