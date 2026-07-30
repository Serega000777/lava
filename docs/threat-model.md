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
limits. Complaint creation fails closed when the limiter is unavailable. Appeals
require listing ownership and independent moderator review. Public-beta hardening
still requires detection of coordinated multi-account false reporting.

Production SMS, VK, AI and payment integrations remain disabled until credentials, provider reviews and legal policies are approved.
