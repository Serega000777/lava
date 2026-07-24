# Threat model

Primary risks are account takeover, OTP abuse, broken object authorization, malicious uploads, stored XSS, SSRF through remote media, prompt injection, fraudulent listings, moderator abuse, credit double-spend and sensitive-data leakage.

Controls include secure server-side sessions, rate limits in Redis, authorization at service boundaries, MIME/signature validation, EXIF removal, isolated image processing, CSP, allowlisted outbound integrations, immutable audit/credit ledgers, idempotency keys, least privilege and redacted structured logging.

Production SMS, VK, AI and payment integrations remain disabled until credentials, provider reviews and legal policies are approved.

