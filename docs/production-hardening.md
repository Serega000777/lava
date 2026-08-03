# Production hardening

## Implemented baseline

- HttpOnly, secure-in-production server-side session cookies.
- Double-submit CSRF protection for authenticated mutations.
- Exact Origin validation for unsafe requests.
- Redis rate limiting on registration, password login and OTP endpoints.
- Fail-closed authentication when the rate limiter is unavailable.
- Request IDs, structured redacted access logs and baseline security headers.
- Hidden, strong-token-protected, low-cardinality OpenMetrics export.
- Web CSP, frame blocking and restricted browser capabilities.

## Deployment requirements

- Use HTTPS at every public edge and set `APP_ENV=production`.
- Set `CORS_ORIGINS` to explicit trusted origins; never use a wildcard with
  credentialed requests.
- Keep PostgreSQL and Redis private and require authentication and encryption where
  supported by the hosting provider.
- Rotate session secrets and provider credentials through a secrets manager.
- Send JSON logs to restricted storage with retention and redaction controls.
- Alert on sustained `429`, `503`, authentication failure and moderation anomaly
  rates.
- Store and rotate `METRICS_TOKEN` in the secrets manager; scrape every API
  instance and the queue/worker gauges before enabling production alerts.

## Pre-launch follow-ups

- Replace the compatibility CSP allowances with per-request script/style nonces.
- Put account-level progressive delays and provider-side OTP limits behind the
  Redis edge limit.
- Add edge/WAF volumetric protection and trusted-proxy client-IP handling.
- Run dependency, container, SAST and DAST scanning in CI.
- Complete backup-restore, incident-response and session-revocation drills.
