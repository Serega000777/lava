# ADR 0010: Provider-isolated AI assistance and append-only credits

Status: accepted

AI suggestions are generated from an immutable listing snapshot through a provider port. The local deterministic provider is the enabled development adapter. A production OpenAI adapter remains disabled until an API key, evaluation set and cost limits are configured.

Text assistance costs one credit. A generation reservation, debit and ledger balance are committed before provider work; provider or output-validation failure produces a compensating refund. Client request UUIDs make retries idempotent. PostgreSQL prevents ledger updates and deletes with an append-only trigger.

Generated text never mutates a listing automatically. The owner reviews and explicitly accepts a completed suggestion while the listing is still a draft. Accepted fields are permanently labeled `AI-assisted` in public responses.

For a future OpenAI implementation, use the Responses API with structured output. The text-improvement workload is a balanced, repeatable worker role, so evaluate `gpt-5.6-terra` before using the Sol flagship for every request. Preserve a lean outcome-first prompt: improve clarity, retain every supplied fact and defect, invent nothing, and return only the title/description schema.
