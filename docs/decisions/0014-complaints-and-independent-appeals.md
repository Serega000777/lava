# ADR 0014: Complaints and independent appeals

## Status

Accepted.

## Decision

Complaints and appeals are first-class PostgreSQL records with bounded states,
reason codes, ownership snapshots and moderator attribution. User retries are
idempotent and protected by database uniqueness constraints.

An appeal cannot be reviewed by the moderator responsible for the original
decision. A successful appeal creates a new moderation case and returns the
listing to pending review instead of activating it directly.

## Consequences

The workflow remains auditable and safe under retries and concurrent decisions.
Moderation capacity must support independent review. Automated user sanctions,
legal takedown handling and complaint-rate abuse detection are separate future
policies rather than hidden side effects of this workflow.
