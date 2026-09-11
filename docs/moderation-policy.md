# Moderation policy

Every submitted listing creates one moderation case. Moderators may claim open cases and record exactly one decision: approve, reject, or request changes. A reason code is mandatory and the optional internal comment is never exposed as seller-facing policy text.

Decisions are append-only audit records. Approval activates the listing, rejection marks it rejected, and a change request returns it to draft. Concurrent claim and decision operations lock the case row; a case claimed by another moderator cannot be decided.

A corrected draft may be submitted again and receives a new case. The database permits historical cases but enforces at most one open case per listing.

Ordinary users cannot access the moderation API. Ownership and moderation authorization are separate controls.

User complaints and owner appeals follow the workflow in
`complaints-and-appeals.md`. Complaint and appeal decisions lock their rows to
prevent double decisions. An overturned appeal never publishes content directly:
it creates a new moderation case for independent review.
