# Moderation policy

Every submitted listing creates one moderation case. Moderators may claim open cases and record exactly one decision: approve, reject, or request changes. A reason code is mandatory and the optional internal comment is never exposed as seller-facing policy text.

Decisions are append-only audit records. Approval activates the listing, rejection marks it rejected, and a change request returns it to draft. Concurrent claim and decision operations lock the case row; a case claimed by another moderator cannot be decided.

Ordinary users cannot access the moderation API. Ownership and moderation authorization are separate controls.

