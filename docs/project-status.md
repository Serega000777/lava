# Project Status

## Current phase

Listings — ready to start after Auth and Profiles review.

## Completed

- Product and architecture baseline drafted.
- Separate Git repository and GitHub target selected.
- Monorepo source, local infrastructure, initial migration, seed and UI prepared.
- Frontend lint, strict typecheck, unit test and production build pass.
- API Ruff lint and health test pass.
- npm production/development dependency audit reports zero known vulnerabilities.
- Docker Compose configuration validates.
- Full Docker stack starts successfully; API and dependencies report healthy.
- Initial Alembic migration applies and the idempotent seed creates cars, goods and services.
- Web responds on port 3000; API health and readiness respond on port 8000.
- Foundation bootstrap is published to GitHub and CI passes.
- Auth domain includes users, password credentials, revocable sessions, roles and verification levels.
- Password auth uses Argon2id; development OTP is hashed/rate-limited in Redis.
- Login and profile pages are implemented.
- Migration 0002 and complete password/OTP/profile/logout flows pass in Docker.

## In progress

None.

## Blocked

None.

## Next tasks

- Add category attributes and listing lifecycle.
- Implement drafts, media metadata and ownership authorization.

## Known limitations

Production SMS and VK providers are disabled. CSRF tokens and account recovery are scheduled before public beta.

## Technical debt

Queue implementation, request IDs, metrics and S3 bucket bootstrap must be completed in the next infrastructure slice.

## Decisions needed from owner

None for the foundation.

## Last verified commands

- `npm run lint` — passed.
- `npm run typecheck` — passed.
- `npm run test` — passed.
- `npm run build` — passed.
- `npm audit` — zero vulnerabilities after patched transitive overrides.
- `python -m ruff check apps/api` — passed.
- `python -m pytest apps/api/tests -q` — passed.
- `docker compose config --quiet` — passed.
- `docker compose up --build -d` — passed; six services running.
- `GET /health` — 200, status `ok`.
- `GET /ready` — 200, status `ready`.
- `GET http://localhost:3000` — 200.
- PostgreSQL seed query — cars, goods and services present.
- `python -m pytest apps/api/tests -q` — 5 passed.
- Auth Docker flow — register, cookie session, `/me`, profile update, logout and OTP passed.
- Invalid password — 401; revoked/logout session — 401; OTP rate limit — 429.
- Alembic version — `0002`.

## Latest successful test run

2026-07-24: local web 1 passed; local API 5 passed; frontend production build and Docker auth integration passed.
