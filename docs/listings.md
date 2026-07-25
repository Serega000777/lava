# Listings

Listings begin as owner-only drafts. An owner may create, read, update or delete a draft. Ownership failures deliberately return `404` so the API does not reveal whether another user's private draft exists.

Submitting a complete draft moves it to `pending_moderation`; it can no longer be edited or deleted through draft endpoints. Required category attributes are data-driven and validated before submission.

Endpoints:

- `GET /categories`
- `POST /listings`
- `GET /listings/mine`
- `GET/PATCH/DELETE /listings/{id}`
- `POST /listings/{id}/submit`

Public active-listing discovery is part of the Search milestone, not this owner workflow.

