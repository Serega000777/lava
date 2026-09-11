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
account data.

Complaint creation uses an atomic Redis script with two fixed-window limits: per
account and per account/listing pair. A retry with the same client request UUID
reproduces its original allow/deny decision and does not consume the limit again.
Redis keys contain hashes instead of public
identifiers. If Redis is unavailable, complaint creation fails closed while
unrelated marketplace functions remain available.

The defaults are 10 unique complaints per account and 3 per account/listing pair
per 24 hours. Deployments may override all limits through environment settings.
The moderator queue computes an advisory coordination signal across a rolling
24-hour window. It combines a burst of at least three distinct reporters with
reason concentration and/or at least three accounts created during the previous
seven days. At least two indicators are required for a warning. The signal cannot
automatically dismiss a complaint, restrict a listing or sanction an account, and
reporter identifiers are not exposed to the browser.
