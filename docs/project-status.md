# Project Status

## Current phase

Messaging Block Lists — implementation and local verification complete.

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
- Moderation queue, claims, decisions and append-only audit records are implemented.
- Migration 0004 and role/decision/audit behavior pass in Docker.
- Pre-merge audit fixed repeat moderation cycles and constrained decision reason codes.
- Public active-listing search, filters, sorting and bounded pagination are implemented.
- PostgreSQL search is isolated behind an application port and backed by trigram indexes.
- The home search and responsive results page are connected to the API.
- Search and Discovery PR merged into `main`.
- Private, idempotent active-listing favorites API is implemented.
- Search cards and the dedicated Favorites page share one reusable listing card.
- Listing images are normalized to metadata-free WebP, stored in private S3-compatible
  storage and exposed publicly only for active listings.
- Authenticated listing complaints and independent owner appeals are implemented.
- Phone verification, audited level decisions and public trust badges are implemented.
- Atomic account and account/listing complaint rate limits are implemented.
- Purpose-bound password recovery and active-session management are implemented.
- Explainable, moderator-only coordinated complaint signals are implemented.
- Durable notification outbox, retrying worker and administrator queue metrics are implemented.
- Private low-cardinality OpenMetrics-compatible technical export is implemented.
- Idempotent account/conversation message rate limits are implemented.
- Private bidirectional messaging block controls are implemented.

## In progress

None.

## Blocked

None.

## Next tasks

- Add production identity provider only after owner legal/security decision.
- Add device/browser metadata to sessions after privacy review.
- Add privacy-reviewed network/device correlation only if advisory complaint
  signals prove insufficient during beta.

## Known limitations

Production SMS and VK providers are disabled. Recovery currently uses the local
OTP adapter and must not be enabled publicly until an approved SMS provider exists.

The earlier local Docker BuildKit hang was resolved by reducing the build context;
the current API image rebuilds successfully and passes the complete verification.

## Technical debt

Alert routing, dashboards and metrics retention remain deployment-specific.
Message reporting and mute controls remain for public-beta hardening.

## Decisions needed from owner

- Select and legally review a production identity/liveness provider before
  enabling document or biometric verification.

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

2026-08-14: a fresh API image built successfully; API Ruff and 87 tests passed;
frontend lint, strict typecheck, 10 tests and production build passed;
migration 0015 applied successfully and is at head.

## Messaging block lists verification

- An authenticated user can idempotently block or unblock another active user.
- Self-blocking and messaging in either blocked direction return safe `409` errors.
- Existing conversation history remains readable while new conversations and
  messages are rejected server-side, including a second check before persistence.
- The private bounded block list exposes only user ID, display name and timestamp.
- The inbox loads block state, supports block/unblock and disables sending for the
  current user's blocks while preserving history.
- A fresh API image built successfully; API Ruff and 87 tests passed on that image.
- Frontend lint, strict typecheck, 10 tests and production build passed.
- Alembic upgrade completed successfully; PostgreSQL reports `0015 (head)`.

## Private metrics export verification

- Export is disabled when `METRICS_TOKEN` is empty and weak non-empty tokens are
  rejected during configuration validation.
- Missing and incorrect Bearer tokens return the same hidden `404` response.
- Secret comparisons are constant-time and tokens never appear in metric output.
- HTTP labels contain registered route templates rather than concrete URLs.
- Exported data is limited to HTTP aggregates, queue state and worker health.
- Redis metric failure degrades the worker gauge without exposing an exception.
- API Ruff and 78 tests passed using a freshly rebuilt image.
- Frontend lint, strict typecheck, 9 tests and production build passed unchanged.
- Docker Compose validated and Alembic remains at `0014 (head)`.

## Message spam protection verification

- Atomic Redis Lua applies per-account and per account/conversation limits.
- Request UUID keys preserve the original allow/deny result, preventing both
  double counting and retry bypass after a denial.
- Identifier-bearing limiter keys are SHA-256 hashes.
- Redis outage fails message creation closed without affecting conversation reads.
- `429` includes `Retry-After`; the web UI explains `429`/`503` and keeps draft text.
- API Ruff and 83 tests passed against current bind-mounted source.
- Frontend lint, strict typecheck, 10 tests and production build passed.
- Fresh API image rebuild remains pending due the documented local BuildKit hang.

## Transactional queue verification

- Notification and outbox rows commit in the same database transaction.
- Unique topic/source keys make enqueue retries idempotent.
- Worker claims with `SKIP LOCKED`, recovers stale locks and applies bounded
  exponential retries before terminal failure.
- Redis Streams are bounded, user identifiers in stream keys are hashed and event
  payloads exclude message bodies and profile data.
- Administrator metrics expose backlog, failures, oldest pending age and heartbeat
  health without failing when Redis metrics are unavailable.
- A real outbox task completed in one attempt and appeared in Redis Stream; its
  isolated smoke-test records were removed afterward.
- API and worker Ruff passed; 72 API tests passed on freshly rebuilt images.
- Frontend lint, strict typecheck, 9 tests and production build passed.
- Docker Compose validated and Alembic reports `0014 (head)`.

## Coordinated complaint detection verification

- A rolling 24-hour signal counts each reporter once per listing.
- Warnings require at least two explainable indicators: reporter burst, reason
  concentration or a cluster of accounts created during the previous seven days.
- Signals are moderator-only and never trigger automatic enforcement.
- Reporter identifiers and account creation timestamps remain server-side.
- The moderation queue is bounded to at most 100 records per request.
- API Ruff and 67 tests passed using a freshly rebuilt API image.
- Frontend lint, strict typecheck, 9 tests and production build passed.
- Docker Compose configuration validated; no migration was required.

## Account recovery and session verification

- Login and recovery OTP values use separate Redis namespaces.
- OTP expires after five minutes and is destroyed after five failed attempts.
- Issuing a new OTP resets only that purpose's attempt counter.
- Recovery endpoints are covered by the fail-closed auth rate limiter.
- Successful password reset revokes every old session before issuing a new one.
- Session DTO excludes token and token hash fields.
- Users can revoke one non-current session or all other sessions.
- Frontend provides recovery and active-session management flows.
- API Ruff and 65 tests passed using a freshly rebuilt API image.
- Frontend lint, strict typecheck, 9 tests and production build passed.
- Docker Compose configuration validated; migrations remain at 0013.

## Complaint abuse protection verification

- Atomic Redis Lua script applies per-account and per account/listing limits.
- Duplicate idempotency request UUIDs do not consume the limit twice.
- Redis keys hash account, listing and request identifiers.
- Limit responses return 429 with `Retry-After`.
- Redis outages fail complaint creation closed with 503.
- Search UI explains limit and temporary security dependency failures.
- Real local Redis smoke check allowed a fresh complaint attempt.
- API Ruff and 56 tests passed using a freshly rebuilt API image.
- Frontend lint, strict typecheck, 8 tests and production build passed.
- Docker Compose configuration validated.

## Verification and trust badge verification

- Successful OTP raises an account to phone-verified level.
- Password registration alone leaves the account unverified.
- Administrator level changes lock the user row and create an attributed decision.
- Organization level is rejected for non-company accounts.
- Verification decisions are protected from update/delete by a PostgreSQL trigger.
- Public trust profile schema excludes phone, reviewer and evidence data.
- Search cards display centrally derived seller badges without affecting ranking.
- Profile UI renders human-readable verification levels.
- API Ruff and 50 tests passed using a freshly rebuilt API image.
- Frontend lint, strict typecheck, 8 tests and production build passed.
- Migrations 0012 and 0013 applied; the append-only trigger exists in PostgreSQL.

## Complaints and appeals verification

- Migration 0011 applied successfully.
- Self-complaints and complaints against non-active listings are rejected.
- Complaint retries are idempotent; changed payload reuse returns a conflict.
- Complaint decisions use bounded decision/resolution pairs and row locking.
- Confirmed listing restrictions archive the listing transactionally.
- Appeals require listing ownership and an appealable moderation decision.
- The original moderator cannot review the appeal.
- Overturned appeals create a new moderation case instead of publishing directly.
- Moderator UI exposes separate listing, complaint and appeal queues.
- Search cards expose an authenticated complaint action.
- API Ruff and 46 tests passed using a freshly rebuilt API image.
- Frontend lint, strict typecheck, 7 tests and production build passed.

## Listing media verification

- Migration 0010 applied successfully.
- JPEG, PNG and WebP inputs are decoded by content and normalized to WebP.
- EXIF metadata is removed and pixel/file limits are enforced.
- Image normalization runs outside the async event loop.
- Failed metadata transactions roll back before best-effort S3 cleanup.
- Private draft media is excluded from the public media endpoint by query design.
- API Ruff and 39 tests passed using a freshly rebuilt API image.
- Frontend lint, strict typecheck, 6 tests and production build passed.

## Moderation verification

- Ordinary user queue access — 403.
- Moderator claim and approve — passed.
- Listing transitioned to active — passed.
- Duplicate decision — 409.
- Immutable audit rows — 1.
- Alembic version — `0004`.
- Audit regression: changes requested → corrected draft → resubmit → approve passed.
- Historical cases/decisions — 2/2; only one open case is permitted.
- Invalid reason code — 422.

## Search verification

- Alembic version — `0005`.
- Active-only public discovery — passed; drafts are excluded.
- Text query, case-insensitive city filter and price sorting — passed.
- Bounded offset pagination — passed.
- Literal SQL wildcard handling — passed.
- Public DTO omits owner, status and internal update timestamp.
- Search page and homepage form regression tests — 2 passed.

## Favorites verification

- Alembic version — `0006`.
- Guest read — 401.
- Duplicate `PUT` — one database row.
- Repeated `DELETE` — 204 and an empty collection.
- Favorite rows are private to the authenticated session.
- API tests — 18 passed.
- Frontend lint, typecheck, 3 tests and production build — passed.
- Docker Favorites page — 200.
- Favorites PR merged into `main`.
- Listing-scoped conversations, idempotent messages and transactional notifications are implemented.
- Responsive inbox UI and seller contact action are implemented.

## Messaging verification

- Alembic version — `0007`.
- Conversation and message retries preserve one row and identifier.
- Changed payload for an existing client message key — 409.
- Foreign conversation access — 404.
- One created message and two transactional recipient notifications persisted.
- Notification kinds — `new_conversation`, `new_message`.
- Duplicate `(sender_id, client_message_id)` rows — zero.
- Notification read transition — passed.
- Messages page — 200.
- Messaging PR merged into `main`.
- Immutable interaction-backed reviews and public reputation summaries are implemented.
- The inbox displays counterpart reputation and provides an eligible review form.

## Reviews verification

- Alembic version — `0008`.
- Review before two-sided messaging — 409.
- One immutable review per conversation and reviewer — enforced; duplicate returns 409.
- Buyer and seller reputation aggregates — `5.00/1` and `4.00/1`.
- Unknown public user — 404.
- Public review DTO omits conversation and participant UUIDs.
- API tests — 27 passed.
- Frontend lint, typecheck, 4 tests and production build — passed.
- Docker Messages page with reputation UI — 200.
- Reviews and Reputation PR merged into `main`.
- Provider-isolated text assistance, idempotent credit reservation and explicit acceptance are implemented.
- Accepted AI fields are labeled in public listing cards.

## AI and credits verification

- Alembic version — `0009`.
- First access welcome balance — 10; one generation balance — 9.
- Repeated client request UUID — same generation and one debit.
- Explicit acceptance is idempotent and marks `title,description` as AI-assisted.
- Source defect text remained present after assistance.
- Ledger rows — one grant and one debit; direct UPDATE blocked by PostgreSQL trigger.
- Provider output limits trigger a compensating refund path.
- API tests — 29 passed.
- Frontend lint, typecheck, 4 tests and production build — passed.
- Docker AI listing page — 200.
- External OpenAI adapter — intentionally pending API credentials and evaluation set.
- AI Assistance and Credits PR merged into `main`.
- Truthful seller and permission-gated administrator analytics are implemented.
- API request IDs and baseline API/Web security headers are implemented.

## Analytics and hardening verification

- Seller metrics returned exactly one owned listing and no foreign rows.
- Metrics use durable favorites, conversations, messages and reviews only.
- Ordinary user access to administrator aggregates — 403.
- Administrator aggregate users/listings — passed.
- API response includes generated `X-Request-ID` and `nosniff`.
- Web response includes `X-Frame-Options: DENY`.
- Analytics page — 200.
- API tests — 30 passed.
- Frontend lint, typecheck, 5 tests and production build — passed.
