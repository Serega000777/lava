# ADR 0031: Review disputes use separate immutable decisions

Status: accepted

The reviewed party may open one dispute per review. Opening a dispute never hides
the review: otherwise a seller could suppress criticism without evidence. An
authorized moderator who is neither review participant records one final `keep`
or `exclude` decision. There is no automatic account sanction.

Reviews, replies and dispute text are never rewritten. Disputes and moderation
decisions are separate records protected against updates. Composite foreign keys
enforce that only `reviewee_id` can own the dispute. A row lock and unique decision
constraint serialize concurrent moderators. Reason codes are bounded and must be
consistent with the outcome.

An `exclude` decision removes the review from public lists and reputation
aggregation while preserving it in the reviewed user's private history and the
moderation audit trail. `keep` leaves public behavior unchanged. This provides
transparent correction without destructive deletion or silently changing the
rating itself.
