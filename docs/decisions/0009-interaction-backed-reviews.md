# ADR 0009: Interaction-backed, immutable reviews

Status: superseded by ADR 0029

A review requires an existing conversation in which both participants have sent at least one message. Opening a conversation alone is not a platform-recorded interaction. Each participant may publish at most one immutable review per conversation, and the reviewed user is always the other participant.

Ratings are database-constrained to 1–5. Public review responses expose the reviewer's display name but never phone, participant UUIDs, conversation ID, session or moderation data. Unknown user IDs return `404` instead of a misleading zero reputation.

Reputation is the transparent average and count of eligible reviews. It is not yet a ranking signal. Bayesian weighting, abuse analysis and moderation can be introduced later without silently changing organic search.
