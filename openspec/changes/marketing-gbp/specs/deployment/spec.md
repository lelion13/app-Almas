## ADDED Requirements

### Requirement: Marketing GBP secrets and public webhooks

Production and local env templates MUST document (without committing secrets):
- Telegram bot token, allowlist user ids, admin chat id, webhook secret
- Google OAuth client id/secret, redirect URI, GBP account/location resource names
- Encryption key for GBP tokens (shared with MP Fernet key or dedicated)
- Pub/Sub push audience / verification settings for the reviews webhook

Public HTTPS routes MUST be reachable for:
- `POST /api/v1/marketing/telegram-webhook`
- `POST /api/v1/marketing/google-pubsub-webhook`
- GBP OAuth callback under `/api/v1/marketing/...`

Operators MUST configure a GCP Pub/Sub push subscription targeting the production Pub/Sub webhook URL.

### Requirement: Marketing GBP migration

Applying this change MUST add an Alembic revision after current head **017** for persisted GBP reviews (and GBP OAuth token storage as designed). Product head MUST be updated in deployment/config when the migration ships.
