# Authentication

The foundation supports password registration/login and development OTP behind feature flags. Production SMS and VK remain disabled.

Passwords use Argon2id. Phones must use E.164 form. Opaque sessions are stored as hashes and delivered through HttpOnly, SameSite=Lax cookies which become Secure in production.

Endpoints: `POST /auth/register/password`, `POST /auth/login/password`, `POST /auth/otp/request`, `POST /auth/otp/verify`, `POST /auth/logout`, `GET /me`, and `PATCH /me`.

Never enable or return the local OTP code in production.

Successful OTP verification raises the account to phone-verified level and writes
an append-only verification decision. Higher identity levels and public badges
are documented in `verification.md`; password registration alone does not prove
control of the supplied phone number.
