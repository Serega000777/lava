# ADR 0035: Authenticated DAST runs only against an ephemeral isolated stack

Status: accepted

Lava runs OWASP ZAP 2.17.0 against an API stack created for one CI run. The
Compose project name includes the GitHub run and attempt identifiers, secrets are
generated at runtime, external OTP/OAuth providers are disabled, and cleanup
removes containers, networks, volumes and the temporary `.env`. The scan must
never target a shared staging or production environment because active rules can
mutate and delete data.

The bootstrap creates a random test account and verifies its session directly.
ZAP receives the cookie only through its header-authentication environment
variable, while the committed plan contains no session material. Before importing
the contract, a generated OpenAPI copy removes every `/auth` and `/internal` path.
This prevents the scanner from revoking its own session or probing private
operational endpoints. A ZAP requestor job requires `GET /me` to return `200`
before the scan continues. A fixed test-only double-submit value and the allowed
Origin header let the isolated session exercise protected unsafe methods without
weakening application CSRF validation.

The image is pinned by digest and the Automation Framework plan bounds threads,
request delay, per-rule time, total scan time and alerts per rule. HTML and JSON
reports are retained for 14 days. ZAP's exit policy and a separate fail-closed JSON
parser both reject HIGH-risk alerts; malformed or missing reports also fail the
workflow. Lower-risk findings remain visible for review and must not be silently
suppressed. Any future exception requires a documented, expiring security decision
rather than an inline allowlist entry.
