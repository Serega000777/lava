# Complaints and appeals

Authenticated users may report an active listing. The listing owner cannot report
their own listing. A complaint contains a bounded reason code and optional details;
the API does not accept arbitrary workflow states from clients.

Complaint creation is idempotent per reporter and client request UUID. Reusing the
same UUID with a different listing or payload returns a conflict. Database
constraints and transaction recovery also protect concurrent retries.

Moderators may resolve or dismiss an open complaint exactly once. Resolution and
reason codes must form an allowed pair. Confirming `listing_restricted` archives
the listing in the same transaction. Complaint decisions do not automatically ban
users; account sanctions require a separate audited policy and workflow.

Only the owner of a listing may appeal its rejected or change-requested moderation
case. One appeal is allowed per case. The moderator who made the original decision
cannot review the appeal. Upholding keeps the existing state. Overturning returns
the listing to `pending_moderation` and creates a new open case for independent
review; it does not silently publish the listing.

Public responses do not expose reporter identifiers, moderator comments or internal
account data. Rate limits and abuse scoring remain required before public beta.
