# Threat model

Primary risks are account takeover, OTP abuse, broken object authorization, malicious uploads, stored XSS, SSRF through remote media, prompt injection, fraudulent listings, moderator abuse, credit double-spend and sensitive-data leakage.

Implemented controls include secure server-side sessions, double-submit CSRF and
Origin validation, fail-closed authentication rate limits in Redis, authorization
at service boundaries, CSP and browser security headers, immutable audit/credit
ledgers, idempotency keys and payload-free structured request logging.

Planned controls include MIME/signature validation, EXIF removal, isolated image
processing, allowlisted outbound integrations, nonce-based CSP, edge volumetric
protection, automated security scanning and verified backup/incident-response
procedures. See `production-hardening.md` for deployment requirements.

Complaint abuse is constrained by authentication, self-report prevention,
bounded reason codes, idempotency keys and atomic per-account/per-target Redis
limits. Complaint creation fails closed when the limiter is unavailable. A
moderator-only, explainable 24-hour signal highlights multi-account bursts without
automatic enforcement or exposing reporter identifiers. Appeals require listing
ownership and independent moderator review. Device and network correlation remain
out of scope until privacy and legal review.

Account recovery uses purpose-bound, one-time, short-lived OTP values and the
same fail-closed Redis rate limiter as login. Successful recovery revokes old
sessions. Public/session DTOs never expose cookie tokens or hashes. Production
hardening still requires an approved SMS provider, SIM-swap response policy and
alerts for repeated recovery attempts.

Password spraying and distributed account targeting are constrained by both the
client/route edge limit and an account-level progressive Redis delay. Limiter and
OTP keys contain only a keyed HMAC-derived phone identity. Existing and unknown accounts execute
Argon2id verification, receive the same credential error and accumulate the same
failure state. Atomic delay updates and compare-and-delete cleanup prevent common
concurrency bypasses. Redis failure closes login; provider-side OTP throttling is
still required before production SMS is enabled.

Background notification delivery uses a transactional outbox, bounded retry
counts and stale-lock recovery. Worker logs exclude payloads; Redis Stream keys
hash user identifiers and stream entries omit message bodies and profile data.
Queue metrics require the administrator analytics permission.

Technical metric export is disabled without a minimum-32-character secret and
returns `404` for unauthorized requests. HTTP metrics use registered route
templates, never concrete URLs, which avoids leaking public UUIDs or creating
attacker-controlled label cardinality. No request body, query, cookie or header is
included in metrics.

Message spam is constrained by authenticated participation checks and atomic
per-account/per-conversation Redis limits. Idempotent retries do not consume the
limit twice, keys hash identifiers and message creation fails closed when the
security dependency is unavailable. Block lists and recipient-level controls
remain a public-beta hardening follow-up.

User-managed block edges prevent contact when either participant has blocked the
other. Checks run before message rate limiting and again at the transactional
service boundary. Blocking never deletes conversation history, preserving evidence
for complaints and moderation. Block lists are private and exclude phone data.

Message reports hide foreign messages with `404`, reject self-reporting, use
hashed fail-closed rate-limit keys and expose message bodies only to moderators.
A single report cannot automatically sanction an account; enforcement requires a
separate explicit and audited workflow.

Conversation mutes are participant-owned and private. They suppress only future
notification/outbox creation; message persistence, evidence and conversation
ordering remain intact. Foreign conversation IDs return `404`.

Read receipts require conversation participation and atomically update only
messages sent by the other participant. Lava does not expose online presence,
last-seen time or reader device data.

Message images are signature-decoded, pixel/byte/count bounded, metadata-stripped
and re-encoded before private storage. Uploads require message ownership and an
unblocked conversation; reads require participation or moderator permission.
Message locks serialize uploads with reports so reported evidence cannot change.

Delivery receipts require participant authorization and an explicit recipient
client acknowledgment. They reveal no presence, last-seen, typing or device data;
read implies delivery and neither timestamp is derived from queue dispatch.

Conversation unread counts are computed only for the authenticated participant's
incoming messages. They do not expose the counterpart's unread state. Opening a
conversation clears only that participant's related notification rows in the same
transaction as message read receipts. A conversation row lock serializes this
operation with sends, preventing contradictory private counters under concurrency.

Message exchange alone no longer unlocks reviews. A transaction becomes reviewable
only after both authenticated conversation participants explicitly confirm it.
Row locks prevent lost confirmation races, database constraints reject partial
completion, and triggers prevent confirmation or review history from being
rewritten. The API returns role-relative booleans rather than either party's private
confirmation timestamp. Collusive confirmations remain possible and require the
planned anomaly, dispute and moderation workflows before reputation affects search.

Review replies require the authenticated reviewee and hide foreign review IDs with
`404`. PostgreSQL independently enforces that the reply author matches the reviewee,
allows one reply per review and rejects later text mutation. Public reply DTOs omit
author UUIDs. Replies cannot erase, change or dilute the rating; abuse reports and
moderator annotations remain planned as separate audit records.

Review disputes are limited to the reviewee by both service authorization and a
composite database foreign key. Filing does not hide criticism. Permission-gated
moderators receive the minimum review evidence needed to decide, and a moderator
who authored or received the review is rejected. Row locks and unique constraints
prevent double decisions. Exclusion affects public display and aggregates without
deleting evidence or triggering an automatic user sanction. Collusion and repeated
cross-account reputation manipulation are highlighted by a separate moderator-only
24-hour aggregate signal. It uses review counts, account age, rating concentration
and repeat relationships, ignores moderator-excluded reviews and requires at least
two indicators. Reviewer identities, phone, device and network data are not exposed
in the signal response. The warning cannot alter ratings, ranking or account state;
false positives require manual review. Privacy-reviewed device or network
correlation remains out of scope.

The Expo test client accepts only a public API origin through `EXPO_PUBLIC_API_URL`;
this value is not a secret. Its API adapter validates response schemas, applies a
bounded timeout and never renders server error bodies. The current shell does not
implement native authentication or persist session material. Private mobile flows
remain disabled until opaque sessions can be stored in OS-backed secure storage,
revoked server-side and transported without weakening browser CSRF protection.

Production SMS, VK, AI and payment integrations remain disabled until credentials, provider reviews and legal policies are approved.
