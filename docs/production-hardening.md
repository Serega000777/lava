# Production hardening

## Implemented baseline

- HttpOnly, secure-in-production server-side session cookies.
- Double-submit CSRF protection for authenticated mutations.
- Exact Origin validation for unsafe requests.
- Redis rate limiting on registration, password login and OTP endpoints.
- Fail-closed authentication when the rate limiter is unavailable.
- Atomic account-level progressive password delays with hashed Redis identities,
  generic unknown-account behavior and race-safe success cleanup.
- Request IDs, structured redacted access logs and baseline security headers.
- Hidden, strong-token-protected, low-cardinality OpenMetrics export.
- Docker build context excludes Git metadata, local dependencies, caches and all
  `.env` variants so they cannot be copied into build transfers accidentally.
- Web CSP, frame blocking and restricted browser capabilities.

## Deployment requirements

- Use HTTPS at every public edge and set `APP_ENV=production`.
- Set `CORS_ORIGINS` to explicit trusted origins; never use a wildcard with
  credentialed requests.
- Keep PostgreSQL and Redis private and require authentication and encryption where
  supported by the hosting provider.
- Set a unique `RATE_LIMIT_KEY_SECRET` of at least 32 random characters and rotate
  it with provider credentials through a secrets manager. Production startup
  rejects the local and example values.
- Send JSON logs to restricted storage with retention and redaction controls.
- Alert on sustained `429`, `503`, authentication failure and moderation anomaly
  rates.
- Store and rotate `METRICS_TOKEN` in the secrets manager; scrape every API
  instance and the queue/worker gauges before enabling production alerts.

## Pre-launch follow-ups

- Replace the compatibility CSP allowances with per-request script/style nonces.
- Put provider-side OTP limits behind the Redis edge limit when the approved SMS
  provider is selected.
- Add edge/WAF volumetric protection and trusted-proxy client-IP handling.
- Run dependency, container, SAST and DAST scanning in CI.
- Complete backup-restore, incident-response and session-revocation drills.
