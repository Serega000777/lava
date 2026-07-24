# Lava

Lava is an AI-assisted classifieds platform for cars, goods and services. The first foundation is a modular monolith with a Next.js web app, FastAPI API, PostgreSQL, Redis, MinIO and a background worker.

## Quick start

1. Copy `.env.example` to `.env`.
2. Run:

```bash
docker compose up --build
```

Open:

- Web: http://localhost:3000
- API docs: http://localhost:8000/docs
- API health: http://localhost:8000/health
- MinIO console: http://localhost:9001

The API applies migrations and seeds the three initial categories on startup. Local credentials are development-only and must be replaced outside local environments.

## Verification

```bash
npm ci
npm run check
python -m pytest apps/api/tests
docker compose config
```

Product scope, architecture, roadmap and current verification status live in `docs/`.

## Development authentication

Password and local OTP flows are enabled only for local development. Phone numbers use E.164 format. The OTP request endpoint returns `dev_code` only when `APP_ENV=development`; never enable this behavior in production. See `docs/authentication.md`.
