# 0020: Idempotent message rate limits

## Decision

Apply atomic Redis fixed-window limits to message creation per account and per
account/conversation pair. A hashed `(account, client_message_id)` key stores the
original allow/deny decision, so a network retry neither consumes the limits twice
nor bypasses a previous denial. Redis keys hash every public
identifier. If Redis is unavailable, message creation fails closed while reads and
other marketplace functions remain available.

## Consequences

Simple burst spam is contained before database writes and notification fan-out.
Clients receive `429` with `Retry-After`; a temporary limiter outage returns `503`.
The limiter does not inspect message bodies and is not a replacement for block
lists, recipient controls or coordinated-abuse analysis.
