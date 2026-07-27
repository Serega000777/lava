# Messaging and notifications

Authenticated endpoints:

- `POST /conversations` opens or returns the buyer's listing conversation.
- `GET /conversations` returns participant-scoped summaries.
- `GET /conversations/{id}/messages` returns a bounded message page.
- `POST /conversations/{id}/messages` accepts a trimmed body and client UUID.
- `GET /notifications` returns private newest-first alerts.
- `PATCH /notifications/{id}/read` marks an owned alert read idempotently.

Conversations can start only for active listings and never with the listing owner as buyer. Message bodies contain 1–4000 characters after trimming. HTML is treated as plain text by the React UI.

Current limitations: polling/realtime transport, abuse rate limits, block lists, attachments and delivery/read receipts are scheduled for hardening. Before public beta, mutations also require explicit CSRF tokens in addition to SameSite cookies.
