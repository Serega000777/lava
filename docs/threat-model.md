# Threat model

Primary risks are account takeover, OTP abuse, broken object authorization, malicious uploads, stored XSS, SSRF through remote media, prompt injection, fraudulent listings, moderator abuse, credit double-spend and sensitive-data leakage.

Implemented controls include secure server-side sessions, double-submit CSRF and
Origin validation, fail-closed authentication rate limits in Redis, authorization
at service boundaries, CSP and browser security headers, immutable audit/credit
ledgers, idempotency keys and payload-free structured request logging.

Planned controls include MIME/signature validation, EXIF removal, isolated image
processing, allowlisted outbound integrations, nonce-based CSP, edge volumetric
protection, automated security scanning and verified backup/incident-response
procedures. See `production-hardening.md` for deployment requirements.

Complaint abuse is constrained by authentication, self-report prevention,
bounded reason codes, idempotency keys and atomic per-account/per-target Redis
limits. Complaint creation fails closed when the limiter is unavailable. A
moderator-only, explainable 24-hour signal highlights multi-account bursts without
automatic enforcement or exposing reporter identifiers. Appeals require listing
ownership and independent moderator review. Device and network correlation remain
out of scope until privacy and legal review.

Account recovery uses purpose-bound, one-time, short-lived OTP values and the
same fail-closed Redis rate limiter as login. Successful recovery revokes old
sessions. Public/session DTOs never expose cookie tokens or hashes. Production
hardening still requires an approved SMS provider, SIM-swap response policy and
alerts for repeated recovery attempts.

Background notification delivery uses a transactional outbox, bounded retry
counts and stale-lock recovery. Worker logs exclude payloads; Redis Stream keys
hash user identifiers and stream entries omit message bodies and profile data.
Queue metrics require the administrator analytics permission.

Technical metric export is disabled without a minimum-32-character secret and
returns `404` for unauthorized requests. HTTP metrics use registered route
templates, never concrete URLs, which avoids leaking public UUIDs or creating
attacker-controlled label cardinality. No request body, query, cookie or header is
included in metrics.

Production SMS, VK, AI and payment integrations remain disabled until credentials, provider reviews and legal policies are approved.
