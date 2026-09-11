# ADR 0032: Reputation abuse signals are advisory and privacy-safe

Status: accepted

Moderators receive an explainable rolling 24-hour signal for accounts with an
unusual series of eligible reviews. The assessor uses only durable platform
records: review count, distinct reviewer count, account age, rating distribution
and repeated reviewer-to-reviewee relationships. Reviews excluded by an
independent moderation decision are ignored.

A warning requires at least two fixed indicators: five or more reviews, three or
more distinct recently created reviewer accounts, at least 90% of three or more
reviews sharing one rating, or at least two repeat reviews from existing reviewer
relationships. These thresholds are intentionally conservative but are not proof
of abuse. The queue is bounded to the 1,000 most active candidates and the API
returns only detected summaries.

The response identifies the account being reviewed but never returns reviewer
identifiers, phone numbers, device fingerprints, network addresses or precise
reviewer account creation times. Signals do not alter public ratings, organic
ranking, verification, account access or moderation state. Every sanction still
requires a separate authorized human decision and auditable workflow. Changes to
data sources, thresholds or automatic effects require a new privacy, fairness and
security review.
