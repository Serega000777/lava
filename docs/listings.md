# Listings

Listings begin as owner-only drafts. An owner may create, read, update or delete a draft. Ownership failures deliberately return `404` so the API does not reveal whether another user's private draft exists.

Submitting a complete draft moves it to `pending_moderation`; it can no longer be edited or deleted through draft endpoints. Required category attributes are data-driven and validated before submission.

Endpoints:

- `GET /categories`
- `POST /listings`
- `GET /listings/mine`
- `GET/PATCH/DELETE /listings/{id}`
- `POST /listings/{id}/submit`
- `POST/GET /listings/{id}/media`
- `DELETE /listings/{id}/media/{media_id}`
- `GET /media/{media_id}` for media attached to active listings

Public active-listing discovery is part of the Search milestone, not this owner workflow.

Draft owners may attach up to ten JPEG, PNG or WebP files of at most 10 MB each.
The API ignores the declared MIME type, decodes the payload, enforces a pixel
limit, applies EXIF orientation and re-encodes to metadata-free WebP before
storage. Original filenames are never used as object keys. Media for non-active
listings is not available through the public endpoint.

Image decoding and normalization run outside the async event loop. If database
metadata persistence fails after an object upload, the transaction is rolled
back and object cleanup is attempted without masking the original failure.
