# ADR 0023: Participant-owned conversation mutes

Status: accepted

## Decision

Each participant may idempotently mute a conversation for their own account. A
mute changes notification delivery only: messages remain writable and readable,
conversation ordering still advances, and the other participant cannot observe
the mute state.

When a new message is committed for a muted recipient, Lava intentionally omits
both the notification row and its transactional outbox task. Unmuting affects
future messages and does not synthesize notifications for earlier messages.

## Consequences

Users gain control over noisy conversations without blocking legitimate contact
or destroying evidence. The setting is private and participant-authorized. The
inbox must remain the durable source for messages because muted conversations do
not produce delivery events.
