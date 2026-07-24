# Data model

The first migration creates `categories(id UUID PK, slug UNIQUE, name, created_at timestamptz)`.

Planned aggregates include users/sessions/verifications, organizations, category attributes, listings/media, moderation cases, favorites, conversations/messages, interactions/reviews, complaints/appeals, notifications, AI jobs/versions, immutable credit ledger entries and audit events. Foreign keys, uniqueness constraints and partial indexes will enforce invariants.

