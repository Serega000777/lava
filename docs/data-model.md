# Data model

The first migration creates `categories(id UUID PK, slug UNIQUE, name, created_at timestamptz)`.

Migration 0003 adds data-driven `category_attributes` and owner-scoped `listings`. Listings store common searchable fields in typed columns and category-specific values in JSONB.

Aggregates include users/sessions/verifications, category attributes,
listings/media, moderation cases, favorites, conversations/messages,
interactions/reviews, complaints/appeals, notifications, transactional outbox
tasks, AI jobs/versions, immutable credit ledger entries and audit events. Foreign
keys, uniqueness constraints and partial indexes enforce invariants.

Migration 0012 adds append-only `verification_decisions`. Sensitive identity
evidence is intentionally excluded from the MVP database.
Migration 0013 enforces decision immutability with a database trigger.
