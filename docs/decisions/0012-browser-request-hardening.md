# ADR 0012: Browser request hardening

## Status

Accepted.

## Context

Lava authenticates browser users with an HttpOnly session cookie. Cookies are sent
automatically by browsers, so authenticated mutations require explicit CSRF
protection. Authentication endpoints also need abuse protection, and production
support needs request correlation without logging sensitive payloads.

## Decision

- Issue a random, readable `lava_csrf` cookie from `GET /auth/csrf`.
- Require the same value in `X-CSRF-Token` for unsafe requests carrying a session
  cookie, using constant-time comparison.
- Reject unsafe requests with an `Origin` outside the configured exact allowlist.
- Rate-limit password and OTP entry points per client address and route in Redis.
  If Redis is unavailable, fail those authentication requests closed with `503`.
- Attach a unique request ID and baseline browser security headers to every API
  response.
- Log method, path, status, duration and request ID as JSON. Do not log query
  strings, request bodies, credentials, cookies or CSRF tokens.
- Apply a restrictive CSP at the Next.js boundary.

## Consequences

The web client must bootstrap and attach a CSRF token to mutations. It retries once
with a fresh token after an explicit `csrf_invalid` response. Deployments must keep
the API origin and CORS allowlist aligned. Redis becomes a required security
dependency for authentication entry points.

The initial CSP permits inline scripts and styles for framework compatibility. A
nonce-based CSP is the next hardening step before a public production launch.
