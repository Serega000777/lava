# Lava repository instructions

Lava is a trustworthy AI-assisted classifieds platform built as a modular monolith.

## Architecture

- `apps/web`: Next.js user interface.
- `apps/mobile`: Expo test client and future native application boundary.
- `apps/api`: FastAPI HTTP API with application, domain, repository and infrastructure boundaries.
- `apps/worker`: background jobs using the same domain contracts.
- `packages`: shared TypeScript packages.
- `infrastructure`: local and production infrastructure assets.
- `docs`: product, architecture, security and operations documentation.

Keep business logic out of React components and HTTP handlers. External services must sit behind interfaces. Brand values live in shared configuration.

## Commands

- `docker compose up --build`: start the complete local foundation.
- `npm ci && npm run check`: validate the web and mobile workspaces.
- `npm run mobile`: start Expo in LAN mode for a physical phone.
- `npm run check:mobile`: lint, typecheck, test and export the Android bundle.
- `python -m pytest apps/api/tests`: run API tests.
- `docker compose run --rm api alembic upgrade head`: apply migrations.
- `docker compose run --rm api python -m app.seed`: seed categories.

## Engineering rules

- TypeScript strict mode and typed Python are mandatory.
- Validate all external input; authorize every protected action server-side.
- Use timezone-aware timestamps, UUID public identifiers and database constraints.
- Never commit credentials, tokens, personal data or generated secrets.
- Never log OTPs, passwords, session tokens or sensitive document fields.
- Every schema change requires an Alembic migration and rollback review.
- API errors use a stable machine code, safe message and request ID.
- Update relevant docs and `docs/project-status.md` with material changes.
- Do not replace a working implementation with a stub without documenting why.
- AI output is untrusted, attributable and must not invent product facts or hide defects.

## Definition of Done

Implementation, authorization, validation, error/loading states, tests, lint, types, build, migrations, documentation and local verification all pass. Review the diff before an intentional commit; never force-push `main`.

Key documents: `docs/product-requirements.md`, `docs/architecture.md`, `docs/threat-model.md`, `docs/project-status.md`, and `docs/decisions/`.
