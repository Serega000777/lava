# ADR 0026: Recipient-confirmed message delivery

Status: accepted

## Decision

`delivered_at` means the recipient's authenticated client successfully loaded the
conversation and acknowledged those incoming messages through an explicit PATCH.
It does not mean that a push notification, Redis event or network request alone
reached a human.

Delivery updates use one atomic `UPDATE ... RETURNING`, target only messages from
the other participant and are idempotent under retries and concurrency. Marking a
message read sets `delivered_at` only when absent, preserving an earlier delivery
timestamp.

## Consequences

The UI can truthfully distinguish `Отправлено`, `Доставлено` and `Прочитано`.
Polling means senders observe status changes after refresh. Lava still does not
publish presence, last-seen, typing activity, device identity or background push
delivery claims.
