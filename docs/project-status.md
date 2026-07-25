# Project Status

## Current phase

Moderation — ready to start after Listings review.

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
- Category attributes, owner-scoped listing drafts and the moderation-submit transition are implemented.
- The web app includes an authenticated draft-creation flow.
- Migration 0003, seeded attributes and listing ownership/lifecycle pass in Docker.

## In progress

None.

## Blocked

None.

## Next tasks

- Review and merge the Listings PR.
- Implement moderation queue, decisions, reasons and audit history.

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
- `python -m pytest apps/api/tests -q` — 8 passed.
- Listings Docker flow — draft, owner update and submit passed.
- Foreign draft read — 404; incomplete submit — 422; edit after submit — 409.
- Alembic version — `0003`.

## Latest successful test run

2026-07-25: local web 1 passed; local API 8 passed; frontend build and Docker Listings integration passed.
