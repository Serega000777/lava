# ADR 0008: Listing-scoped, idempotent messaging

Status: accepted

A buyer has at most one conversation per listing. The seller is captured when the conversation is created, and the database rejects self-conversations. Every participant query is scoped by the authenticated user; inaccessible and absent conversations both return `404`.

Clients supply a UUID `client_message_id`. The `(sender_id, client_message_id)` constraint makes retries safe. Reusing the key in another conversation or with a changed payload returns `409`, preventing an ambiguous successful response.

Message creation and its recipient notification are committed in one transaction. Notification source keys are unique per recipient, so retries do not produce duplicate alerts. The initial implementation is pull-based; realtime delivery can consume the same committed records through an outbox in a later slice.

Conversation, message and notification reads are bounded. Composite indexes follow participant-and-time access paths; redundant single-column indexes were removed during review.
