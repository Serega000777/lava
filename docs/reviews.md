# Reviews and reputation

- `GET /conversations/{id}/interaction` returns the participant-relative deal state.
- `PUT /conversations/{id}/interaction/completion` idempotently confirms the deal
  for the authenticated participant.
- `POST /conversations/{id}/review` creates one immutable participant review after
  both parties have confirmed completion.
- `POST /reviews/{id}/reply` creates the reviewed party's single immutable reply.
- `GET /reviews/received` returns the authenticated reviewee's private review and
  dispute state, including moderator-excluded history.
- `POST /reviews/{id}/dispute` opens one reviewee-owned dispute.
- `GET /moderation/review-disputes` returns the permission-gated open queue.
- `POST /moderation/review-disputes/{id}/decision` records one independent decision.
- `GET /moderation/reputation-signals` returns bounded, aggregated advisory
  signals to users with `moderation:read` permission.
- `GET /users/{id}/reviews` returns bounded newest-first public reviews.
- `GET /users/{id}/reputation` returns the average rating and review count.

The first persisted message changes an interaction from `awaiting_contact` to
`contacted`. Buyer and seller then confirm independently. Only `completed`, which
requires both confirmations, makes a review eligible. A second review from the
same reviewer and interaction returns `409`. Ratings range from 1 to 5; comments
are trimmed and limited to 2,000 characters.

The inbox displays confirmation state and does not render the review form until
the server returns `can_review=true`. React renders comments as plain text.

Contact, confirmation and completion timestamps cannot be rewritten. Reviews are
also immutable at the database layer. A participant can still read history and
confirm an actual transaction after blocking; blocking only prevents new contact.

Only `reviewee_id` may reply. The API hides an ineligible or unknown review with
`404`, returns `409` for a second reply and trims non-empty reply text to 2,000
characters. A composite foreign key enforces the author rule in PostgreSQL. Public
responses nest the responder's display name, text and time without author,
conversation or interaction UUIDs. The profile cabinet lets the reviewed user
reply and then replaces the form with the published immutable response.

A dispute is visible privately as `open`, `keep` or `exclude`, together with the
bounded resolution reason and optional moderator explanation but not moderator ID.
Opening it does not hide the review. A moderator who did not participate in the
interaction may record one final decision. `exclude` removes the review from public responses and rating
aggregation, but the original review, reply, dispute and decision remain separate
audit records. No dispute or single moderation decision automatically sanctions an
account.

A rolling 24-hour reputation signal requires at least two explainable indicators:
a five-review burst, three recently created distinct reviewer accounts, a 90%
rating concentration across at least three reviews, or two repeat reviews from
existing reviewer relationships. Moderator-excluded reviews do not contribute.
The response identifies only the reviewed account and aggregated counts; it omits
reviewer IDs, phone, device and network data. It never changes reputation, ranking
or account state automatically. The moderation UI explicitly presents it as a
manual-review aid.

Before reviews influence discovery ranking, the platform still needs a documented
weighting policy and beta evaluation of signal precision and fairness.
