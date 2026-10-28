# Design: marketing-gbp

## Architecture

```
Telegram ──POST──► /marketing/telegram-webhook ──► telegram_service
                                              ├──► gbp_service.localPosts
                                              └──► gbp_service.reviews.reply

Pub/Sub ──POST──► /marketing/google-pubsub-webhook ──► review ingest
                                              ├──► persist gbp_reviews
                                              ├──► telegram alert
                                              └──► auto-reply (5★ empty)

Admin JWT ──► /marketing/gbp/oauth/* ──► tokens in gbp_connections (Fernet)
```

## Data

- `gbp_connections`: single active OAuth connection (encrypted tokens)
- `gbp_oauth_states`: PKCE/state for connect flow
- `gbp_reviews`: idempotent by `google_review_id`
- `gbp_reply_sessions`: Telegram user awaiting manual reply text

## Auth

- Telegram: `X-Telegram-Bot-Api-Secret-Token` == env secret; allowlist user ids
- Pub/Sub: Bearer Google OIDC JWT (`aud` = push URL or configured audience); soft-fail configurable in dev
- GBP: OAuth refresh via Google token endpoint; calls use Bearer access token

## Libraries

- Telegram Bot HTTP API via `httpx` (webhook JSON) — avoids PTB event-loop coupling
- Google OAuth + GBP REST via `httpx` + `google-auth` for push token verify
- No need for `google-cloud-pubsub` pull client (push only)

## Alembic

**018** — marketing GBP tables
