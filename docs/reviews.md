# Reviews and reputation

- `POST /conversations/{id}/review` creates one immutable participant review.
- `GET /users/{id}/reviews` returns bounded newest-first public reviews.
- `GET /users/{id}/reputation` returns the average rating and review count.

Eligibility requires at least one message from both conversation participants. A second review from the same reviewer and conversation returns `409`. Ratings range from 1 to 5; comments are trimmed and limited to 2,000 characters.

The inbox displays the counterpart's current reputation and provides the review form. React renders comments as plain text.

Before reviews influence discovery ranking, the platform needs anomaly detection, complaint handling and a documented weighting policy.
