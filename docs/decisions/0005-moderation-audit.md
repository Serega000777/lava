# ADR 0005: Moderation cases and append-only decisions

Status: accepted

Each submitted listing owns one moderation case. Case state provides the current queue view; immutable decision rows preserve actor, reason, comment and time. Transactional row locking prevents two moderators from deciding the same case concurrently.

Policy reason codes are stable machine values. User-facing explanations will be mapped separately so internal notes cannot leak accidentally.

