# ADR 0033: Password login uses account-level progressive delays

Status: accepted

The existing edge limiter constrains authentication traffic by client address and
route, but an attacker can rotate addresses while targeting one account. Password
login therefore also tracks failures by an HMAC-SHA-256-derived phone identity in
Redis.
Raw phone numbers and passwords never appear in limiter or OTP keys and the HMAC
secret must be supplied through production secret management.

The first two failures retain the generic `401` response. Starting with the third
failure, an atomic Redis script applies delays of 2, 4, 8 seconds and so on, capped
at five minutes. Failure history expires after one hour. The same work and state
transition apply to existing and unknown accounts; a dummy Argon2id hash reduces
the timing difference that could otherwise reveal registration state.

An active delay returns `429` with a bounded `Retry-After` value before expensive
password verification. A successful login clears observed historical failures by
compare-and-delete, so it cannot erase a concurrent new failure. If Redis becomes
unavailable after the edge check, password login fails closed with `503`. These
controls supplement rather than replace edge limits, provider limits, monitoring
and secure account recovery.
