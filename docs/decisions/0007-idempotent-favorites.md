# ADR 0007: Idempotent, private favorites

Status: accepted

Favorites are a private user-to-listing relation with a composite primary key. `PUT` and `DELETE` are idempotent so retries from browsers and mobile clients cannot create duplicates or turn a successful request into an error.

Only active listings may be added or returned. A removed or archived listing therefore disappears from the user's collection without leaking its lifecycle state. All reads and writes are scoped by the authenticated user from the server-side session.

The list endpoint uses bounded offset pagination. A composite `(user_id, created_at)` index supports the primary newest-first access path without maintaining a redundant global timestamp index.
