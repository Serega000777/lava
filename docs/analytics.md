# Analytics

- `GET /analytics/seller` returns bounded per-listing counts for the authenticated owner.
- `GET /analytics/admin` returns platform totals and requires `analytics:admin`.

Seller counts are derived from existing relational events rather than a separate eventually consistent counter. This favors correctness at the current scale. Materialized aggregates can be introduced after query plans and traffic justify them.

The platform intentionally omits view and conversion figures until it records deduplicated, privacy-reviewed view events. Administrative results contain no phone numbers, message bodies or review text.
