# ADR 0027: Participant-owned conversation unread counters

## Status

Accepted.

## Decision

`GET /conversations` derives `unread_count` from messages in each returned
conversation where the sender is not the authenticated participant and `read_at`
is absent. The count is computed in PostgreSQL with the existing partial unread
index and is not stored separately.

`PATCH /conversations/{id}/read` updates unread incoming messages and the current
participant's unread notification rows for the conversation in one transaction.
A row lock on the conversation serializes the operation with send transactions,
which already advance `conversation.updated_at`. The UI clears a conversation
badge only after that endpoint succeeds.

## Consequences

The API has one authoritative definition of unread state and cannot expose the
counterpart's private count. Derived counts avoid drift and a new migration, while
the correlated aggregate adds bounded work to conversation-list reads. The
existing pagination limit and partial index constrain that cost. Realtime badge
updates remain out of scope; a later transport can refresh the same durable state.
