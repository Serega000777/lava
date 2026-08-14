# Messaging and notifications

Authenticated endpoints:

- `POST /conversations` opens or returns the buyer's listing conversation.
- `GET /conversations` returns participant-scoped summaries.
- `GET /conversations/{id}/messages` returns a bounded message page.
- `POST /conversations/{id}/messages` accepts a trimmed body and client UUID.
- `GET /notifications` returns private newest-first alerts.
- `PATCH /notifications/{id}/read` marks an owned alert read idempotently.

Conversations can start only for active listings and never with the listing owner as buyer. Message bodies contain 1–4000 characters after trimming. HTML is treated as plain text by the React UI.

Message creation has atomic Redis limits per account and per account/conversation
pair. The defaults allow 60 messages per account and 20 per conversation each
minute. Repeating the same client message UUID reproduces its original allow/deny
decision without consuming the window twice; identifier-bearing Redis keys are
hashed. Limiter failure returns `503` only for
message creation, while conversation and message reads remain available.

Current limitations: message reporting, mute controls, attachments and
delivery/read receipts are scheduled for hardening. Realtime notification events are published through the
transactional outbox, while the UI still uses polling as its durable fallback.

User block controls are private and idempotent:

- `PUT /users/{id}/block` blocks an active user;
- `DELETE /users/{id}/block` removes the caller's block;
- `GET /blocks` returns a bounded private block list.

A block in either direction prevents new conversations and messages with `409`,
but leaves history readable. The inbox disables its composer for blocks created by
the current user and keeps the conversation visible.
