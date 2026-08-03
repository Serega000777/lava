# 0018: Transactional outbox queue

## Decision

Store background tasks in PostgreSQL in the same transaction as their source
records. Workers claim tasks with row locking and publish notification events to
bounded Redis Streams. Delivery is at least once; task identifiers are stable for
consumer deduplication. Retry state and terminal failures remain queryable in the
database.

## Consequences

The API cannot commit a notification while silently losing its dispatch task.
Redis outages delay delivery without losing the database notification. PostgreSQL
is used for durable queue state at MVP scale; a dedicated broker may replace the
dispatch adapter later without changing transactional producers.
