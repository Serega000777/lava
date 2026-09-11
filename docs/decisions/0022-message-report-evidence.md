# ADR 0022: Message reports preserve evidence

Status: accepted

## Decision

Message reports use a dedicated table and reference an immutable message. Only a
conversation participant may report an incoming message. The API hides foreign
messages with `404`, rejects reports on a sender's own message and makes retries
idempotent. Account and target limits are enforced atomically in Redis and fail
closed when that security dependency is unavailable.

Moderators with existing moderation permissions receive the referenced message
body in a separate bounded queue. Decisions record the moderator, resolution and
timestamp. A report never automatically suspends or blocks an account.

## Consequences

Recipients can preserve actionable evidence while separately blocking contact.
Sensitive message text is not copied into the report or exposed publicly. Human
review remains necessary, and account enforcement is intentionally deferred to a
future audited sanctions workflow.
