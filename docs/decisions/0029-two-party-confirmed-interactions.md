# ADR 0029: Two-party confirmed interactions gate reviews

Status: accepted; supersedes ADR 0009 eligibility rules

A conversation and an exchange of messages prove contact, not a completed sale or
service. Lava therefore records one interaction per conversation. The first
persisted message records contact, and buyer and seller independently confirm that
the transaction occurred. Completion is reached only after both confirmations and
is the sole state that permits a review.

Confirmation timestamps and completion are immutable. Row locking serializes the
two confirmations, retrying the same confirmation is idempotent, and a database
constraint prevents a completed interaction without both parties. Reviews carry
the interaction ID with a composite foreign key that prevents associating a review
with another conversation. Reviews are database-immutable and remain limited to
one per participant and interaction.

Existing eligible reviews are preserved during migration. Their conversations are
marked completed at the earliest legacy review timestamp; conversations without a
review retain their first-message contact time but require explicit confirmation.
This is a documented compatibility rule, not evidence that legacy confirmations
were collected.

The participant API exposes only role-relative confirmation booleans, completion
time and the caller's review eligibility. It does not expose private participant
IDs or confirmation timestamps. Disputes, review replies and moderation decisions
will be separate audited workflows; they must not rewrite confirmation history.
