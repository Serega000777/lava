# ADR 0024: Atomic recipient-owned read receipts

Status: accepted

## Decision

Messages carry one nullable `read_at` timestamp because MVP conversations have
exactly two participants. Only the recipient may mark messages read, through a
participant-authorized conversation endpoint. The service atomically updates
unread messages from the other sender with `UPDATE ... RETURNING`.

The response contains only the number updated and shared timestamp. It does not
expose reader activity beyond the receipt already visible on the sender's own
messages. Repeated and concurrent requests are idempotent.

## Consequences

Senders receive truthful persisted read state without presence tracking or a
realtime surveillance signal. The inbox remains polling-based, so a sender sees a
new receipt on the next message refresh. Group conversations would require a
separate per-user receipt model and are outside the MVP.
