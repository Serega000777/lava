# ADR 0016: Purpose-bound recovery and session revocation

## Status

Accepted.

## Decision

Password recovery uses a dedicated OTP namespace. A login OTP cannot reset a
password and a recovery OTP cannot be exchanged through the login flow. Recovery
request and confirmation endpoints share the existing fail-closed auth rate limiter.

A successful password reset updates the Argon2id credential and revokes every
existing session before issuing one new session. Active-session APIs expose only
UUID, creation, expiry and whether the session is current; token hashes never
leave the server.

The current session can be ended only through logout. Session-management endpoints
may revoke another owned session or all other sessions.

## Consequences

Compromise of an old cookie does not survive password recovery. Separate OTP
purposes reduce cross-flow token abuse. Production recovery still depends on an
approved SMS provider and requires monitoring for SIM-swap and social-engineering
risk.
