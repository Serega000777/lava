# Background queue

Lava uses a PostgreSQL transactional outbox for durable background work. Creating
a message notification and its `notification.created` task happens in one database
transaction. A unique `(topic, source_key)` constraint makes enqueue retries safe.

The worker claims one available task with `FOR UPDATE SKIP LOCKED`, increments its
attempt counter and publishes the event to a bounded per-user Redis Stream. Tasks
are delivered at least once, so consumers must deduplicate by `task_id`. Temporary
dispatch failures use exponential backoff; five failed attempts move a task to
`failed`. A processing lock older than five minutes is returned to the queue.

The worker never logs task payloads. Per-user stream keys hash the user UUID, and
streams contain notification identifiers and kinds, not message bodies or profile data. Existing database notification
polling remains the source of truth if realtime delivery is delayed.

Administrators with `analytics:admin` may read `GET /analytics/admin/queue`. It
returns status counts, oldest pending age and worker heartbeat health. A missing
Redis heartbeat is reported as unhealthy rather than making the metrics endpoint
unavailable.
