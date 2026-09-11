# 0017: Explainable complaint coordination signals

## Decision

Compute coordination signals from complaints in a rolling 24-hour window when a
moderator reads the complaint queue. A reporter is counted once per listing. The
signal records a reporter burst, concentration on one reason and a cluster of
accounts created during the previous seven days. At least two indicators are
required before the UI displays a warning.

The signal is advisory. It never dismisses a complaint, restricts a listing or
sanctions an account. Moderators must inspect the underlying case and make the
existing audited decision. Reporter identifiers and account creation timestamps
are not returned to the browser.

## Consequences

The result stays current without a derived-state migration or background job and
is explainable to moderators. It detects simple bursts, not shared devices,
payment instruments or organization-level campaigns. Adding those identifiers
requires a separate privacy and legal review.
