# ADR 0005: Moderation cases and append-only decisions

Status: accepted

Each submission cycle creates a moderation case. A partial unique index permits only one open case per listing, while preserving earlier cases after changes are requested and a seller resubmits. Case state provides the current queue view; immutable decision rows preserve actor, reason, comment and time. Transactional row locking prevents two moderators from deciding the same case concurrently.

Policy reason codes are stable machine values. User-facing explanations will be mapped separately so internal notes cannot leak accidentally.
