# Architecture

## System shape

Lava starts as a modular monolith in a monorepo. Web, API and worker are deployable processes; domain modules share one PostgreSQL database but own their schemas and services. External search, object storage, SMS, OAuth, moderation and AI providers are adapters.

```text
Browser -> Next.js -> FastAPI -> PostgreSQL
                         |-----> Redis
                         |-----> S3/MinIO
                         `-----> background queue -> Worker
```

The initial vertical slice contains system health and the category catalog. Future modules: identity, profiles, listings, media, search, moderation, messaging, reputation, AI, credits and admin.

## Data and API conventions

Public entities use UUIDs and timezone-aware timestamps. State changes are transactional and credit operations idempotent. HTTP handlers validate and delegate; repositories isolate persistence. Errors never expose internals and include a request/correlation identifier.

## Deployment

Docker Compose is the supported local path. Production will use separately managed PostgreSQL, Redis and S3-compatible storage without changing domain code. Search begins with PostgreSQL FTS/trigram behind an adapter.

Background work uses a PostgreSQL transactional outbox as durable queue state.
Workers claim rows with `SKIP LOCKED` and publish bounded notification streams to
Redis. This avoids the commit/enqueue gap while preserving replaceable adapters.
