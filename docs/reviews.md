# Reviews and reputation

- `GET /conversations/{id}/interaction` returns the participant-relative deal state.
- `PUT /conversations/{id}/interaction/completion` idempotently confirms the deal
  for the authenticated participant.
- `POST /conversations/{id}/review` creates one immutable participant review after
  both parties have confirmed completion.
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

Before reviews influence discovery ranking, the platform needs anomaly detection, complaint handling and a documented weighting policy.
