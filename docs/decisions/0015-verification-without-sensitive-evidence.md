# ADR 0015: Verification without storing sensitive evidence

## Status

Accepted.

## Decision

The MVP stores only a current verification level and append-only decisions. It
does not store passport scans, document numbers, selfies or biometric templates.
Phone level is granted by OTP. Higher levels require an administrator decision
after an external or manual review.

Public badges are derived centrally and describe completed checks without making
claims about seller reliability. Organization verification is restricted to
company accounts.

## Consequences

The platform can communicate trust without prematurely becoming a sensitive
document repository. A production identity provider will require a new ADR and
legal/security review. Reputation remains a separate aggregate based on actual
platform interactions.
