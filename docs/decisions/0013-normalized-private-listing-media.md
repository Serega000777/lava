# ADR 0013: Normalized private listing media

## Status

Accepted.

## Decision

Listing images are uploaded through the authenticated API and stored in a private
S3-compatible bucket. The API validates decoded content instead of trusting file
extensions or client MIME headers, rejects oversized payloads and pixel counts,
applies orientation, strips metadata and emits WebP. Random object keys contain no
user filenames.

PostgreSQL stores ownership, order, dimensions, type and object-key metadata.
Only owners may mutate media on drafts. Public reads require an active listing and
are proxied by the API, so bucket policy does not become an authorization layer.

## Consequences

The API performs CPU-bound decoding in its process for this first bounded slice.
Public scale should move normalization to an isolated worker with malware scanning
and quarantine while preserving the same database state model. Failed object
cleanup is logged for reconciliation because database authorization state remains
the source of truth.
