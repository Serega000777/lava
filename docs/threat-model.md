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

Production SMS, VK, AI and payment integrations remain disabled until credentials, provider reviews and legal policies are approved.
