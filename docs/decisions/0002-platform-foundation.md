# ADR 0002: Platform foundation

Status: accepted

Use Next.js/TypeScript for web, FastAPI/Python for API, PostgreSQL as the source of truth, Redis for ephemeral state and queues, and an S3-compatible interface with MinIO locally. Search starts with PostgreSQL and remains behind an adapter. Production providers are never referenced directly from domain code.

