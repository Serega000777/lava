# Verification and public trust

LAVA separates authentication, identity evidence and marketplace reputation.
A verification badge states only which checks the platform completed; it does
not guarantee honesty, product quality or successful delivery.

Levels:

0. `Новый` — no verified factor.
1. `Телефон подтверждён` — granted only after successful OTP verification.
2. `Личность проверена` — reserved for an approved identity-provider workflow.
3. `Расширенная проверка` — reserved for an additional approved liveness check.
4. `Организация проверена` — available only to company accounts.

The MVP does not upload or retain passports, selfies or biometric templates.
Levels 2–4 can be attested only by an administrator after an external/manual
review. Every change records an append-only decision with actor, source, previous
level, new level, reason code and timestamp.

Public profile and search responses expose display name, role and derived badge.
They never expose phone numbers, evidence, internal comments or reviewer identity.
Production document and biometric processing requires separate legal, retention,
provider, encryption and incident-response decisions from the owner.
