# ADR 0003: Passwords, OTP and server-side sessions

Status: accepted

Passwords use Argon2id and are stored only as adaptive hashes. Authentication issues a high-entropy opaque token in an HttpOnly, SameSite=Lax cookie; PostgreSQL stores only its SHA-256 digest, expiry and revocation time. This supports immediate revocation without exposing reusable database tokens.

OTP values are short-lived, single-use and hashed in Redis. Requests are rate-limited per phone. A development code is returned only when `APP_ENV=development` and `LOCAL_OTP_ENABLED=true`; production SMS remains disabled until its provider and policy are approved.

Authorization is deny-by-default using stable role-to-permission mappings. Roles never replace resource ownership checks.

