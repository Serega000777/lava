# ADR 0030: One immutable reply from the reviewed party

Status: accepted

Only the user reviewed by a confirmed interaction may publish a reply. Lava stores
at most one reply per review and does not permit editing after publication. This
keeps the public history stable and avoids silent replacement after a buyer has
read or cited a response.

The database enforces authorship with a composite foreign key from
`(review_id, author_id)` to `(review.id, reviewee_id)`, not only with application
authorization. Concurrent duplicate submissions are collapsed by a unique review
constraint and return `409`. A database trigger rejects reply updates; account or
review deletion may still cascade according to the platform retention policy.

Public review responses include the responder's current display name, reply text
and creation time. They exclude author UUID, conversation ID and interaction ID.
Disputes and moderator annotations are separate records and must never rewrite the
original review or reply.
