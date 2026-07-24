# Project Status

## Current phase

Auth and Profiles — ready to start.

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

## In progress

None.

## Blocked

None.

## Next tasks

- Model users, roles, permissions, sessions and verification levels.
- Implement password login and a local-only OTP provider behind feature flags.
- Add profile API/UI and authorization tests.

## Known limitations

Only the first foundation slice is implemented. Production integrations are intentionally absent.

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

## Latest successful test run

2026-07-24: local web 1 passed; local API 1 passed; GitHub Actions run 30094457520 passed.
