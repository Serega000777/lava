# ADR 0011: Truthful analytics and baseline response hardening

Status: accepted

Seller analytics include only durable platform records: favorites, conversations, messages and eligible reviews. The UI does not display views, reach or conversion because Lava does not yet record a trustworthy view event. Results are owner-scoped and bounded.

Administrator totals use a separate `analytics:admin` permission, inherited only by the wildcard admin role. They expose aggregate counts, never user contact details or message content.

API responses receive a generated request ID plus `nosniff`, referrer and browser-permission policies. Next.js adds the same baseline headers and denies framing. Request IDs are not accepted from untrusted clients. Structured log correlation and a nonce-based Content Security Policy remain production-hardening follow-ups.
