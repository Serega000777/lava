# ADR 0006: PostgreSQL search behind an application port

Status: accepted

The first discovery implementation uses PostgreSQL trigram indexes, case-insensitive matching and an explicit relevance expression. The API depends on a small search port instead of exposing PostgreSQL expressions to route handlers.

Only active listings enter public results. Sort values are allowlisted and all filters remain bound query parameters. Search wildcards are escaped as literal user input.

Offset pagination is capped at 10,000 for the MVP. The port keeps a future move to keyset pagination or a dedicated search engine isolated from HTTP contracts.
