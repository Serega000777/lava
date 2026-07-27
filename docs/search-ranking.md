# Search and ranking

`GET /search/listings` is the public discovery endpoint.

Supported inputs:

- `q`: title and description query, up to 200 characters.
- `category_id`, `city`, `price_min`, `price_max`: exact/range filters.
- `sort`: `relevance`, `newest`, `price_asc`, or `price_desc`.
- `limit` and `offset`: bounded pagination (`limit <= 100`, `offset <= 10000`).

Public visibility is enforced in the adapter: only listings in `active` status are returned. Relevance favors an exact title match, then title trigram similarity, then description similarity. Stable secondary ordering prevents unpredictable pages.

The public response deliberately omits owner identifiers, moderation state and internal timestamps.

PostgreSQL needs the `pg_trgm` extension. Migration `0005` enables it and adds trigram and active-discovery indexes. If the production database role cannot create extensions, an administrator must enable `pg_trgm` before applying the migration.

The current ranking deliberately has no paid boost. Reputation, distance and freshness decay can be added later as explicit, testable signals.
