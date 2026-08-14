# 0021: Bidirectional messaging blocks

## Decision

Store user-managed block edges separately from conversations. A block in either
direction prevents starting a new conversation and sending new messages. Existing
conversation history, notifications and reviews remain available. Blocking and
unblocking are idempotent; users cannot block themselves.

Public block responses contain only the blocked user's UUID, display name and the
block timestamp. Phone numbers and the other user's private block state are not
exposed. Messaging checks once before the Redis limiter and again at the service
boundary to avoid both quota consumption and a block/send race.

## Consequences

Recipients gain an immediate spam control without destroying evidence. The block
list is private to its owner. Reporting, administrator safety review, mute controls
and automatic harassment detection remain separate workflows.
