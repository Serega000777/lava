# ADR 0028: Expo mobile test boundary

## Status

Accepted.

## Decision

Add `apps/mobile` as an Expo SDK 57 workspace for physical-phone testing and as
the future native client boundary. The first slice calls only public FastAPI
endpoints and renders a health/category/latest-listing overview. It uses
`packages/api-contracts` for runtime response validation and keeps API access in
a dedicated adapter and feature service.

Expo is not a second implementation of the marketplace domain. Search ranking,
authorization, listing lifecycle, moderation, credits and messaging rules remain
server-side. The mobile client is not included in Docker Compose and is started in
LAN mode because Metro and Expo Go run on the developer workstation and phone.

Native authentication is deferred until the existing revocable session model has
an explicit mobile transport and OS-backed secure storage. The mobile application
must not weaken browser HttpOnly-cookie and CSRF protections.

## Consequences

Public API regressions can now be exercised on a real phone without waiting for a
full mobile product phase. Shared runtime schemas reduce client drift and can be
adopted incrementally by web features. The repository gains a larger Node toolchain
and Android bundle check. Expo/Metro build advisories must be monitored upstream;
an incompatible SDK downgrade is not an acceptable automated audit fix.
