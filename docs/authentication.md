# Authentication

The foundation supports password registration/login and development OTP behind feature flags. Production SMS and VK remain disabled.

Passwords use Argon2id. Phones must use E.164 form. Opaque sessions are stored as hashes and delivered through HttpOnly, SameSite=Lax cookies which become Secure in production.

Endpoints include password and OTP login, logout, `GET/PATCH /me`, password
recovery, and active-session management. See the generated OpenAPI document for
the complete contract.

OTP values are purpose-bound, expire after five minutes and are destroyed after
five failed verification attempts. Request cooldown and endpoint rate limits are
enforced separately.

Never enable or return the local OTP code in production.

Successful OTP verification raises the account to phone-verified level and writes
an append-only verification decision. Higher identity levels and public badges
are documented in `verification.md`; password registration alone does not prove
control of the supplied phone number.

Password recovery uses separate Redis keys from login OTP. A successful reset
re-hashes the password with Argon2id, revokes every previous session and issues
one new current session. Recovery request responses are generic and must not
confirm whether a phone is registered.

`GET /auth/sessions` returns active session identifiers and timestamps without
token hashes. Users may revoke a non-current session or all other sessions. The
current session is ended through `/auth/logout` so cookie deletion remains explicit.
