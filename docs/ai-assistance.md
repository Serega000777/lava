# AI assistance and credits

Endpoints:

- `GET /credits` returns the authenticated user's balance.
- `POST /listings/{id}/ai/text` reserves one credit and returns an idempotent suggestion.
- `POST /ai/generations/{id}/accept` applies a completed suggestion to an owned draft.

Development accounts receive 10 welcome credits on first credit access. The ledger is append-only and records the signed amount, resulting balance and generation reference. Failed or invalid provider output is refunded.

The enabled local provider only normalizes supplied text and adds a neutral request for missing details when the description is empty. It does not infer characteristics. The input snapshot, provider, model, prompt version, result and acceptance time remain auditable.

Production OpenAI calls are intentionally not enabled without credentials. Current implementation guidance is based on the official [Responses API guidance](https://developers.openai.com/api/docs/guides/migrate-to-responses) and [GPT-5.6 prompting guidance](https://developers.openai.com/api/docs/guides/prompt-guidance-gpt-5p6.md).
