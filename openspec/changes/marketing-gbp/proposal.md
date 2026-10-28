# Proposal: marketing-gbp

## Intent

Add a marketing module so Studio ops can publish Google Business Profile posts and manage reviews via Telegram, with real-time review alerts (Pub/Sub) and selective auto-reply. GBP account is linked once via OAuth in Almas admin.

## Scope

### In
- Domain `marketing-gbp`: Telegram webhook + Pub/Sub push webhook + GBP OAuth connect (admin)
- Posts: authorized Telegram users send photo+caption **or** text-only → `localPosts.create`
- Reviews: Pub/Sub `NEW_REVIEW` → persist row → Telegram alert → auto-reply if 5★ and empty text (random fixed phrase) → manual reply via Responder button flow
- Single GBP location IDs in env; Telegram allowlist + admin chat id in env
- Alembic migration for reviews (+ OAuth token store if not reusing a generic secrets table)
- Docs: env examples, short GCP Pub/Sub push setup note in runbook/lessons
- Deps: Telegram bot stack + Google API client libs as needed

### Out
- Public landing page
- Multi-location GBP mapping to Studio sites
- Full reviews UI in web (beyond OAuth connect)
- Edit/delete GBP posts from Telegram
- Auto-reply for ratings other than 5★ empty text
- Mercado Pago / abono payment association

## Approach

- Routers under `/api/v1/marketing/…` (public webhooks with validation; OAuth start/callback admin JWT like MP)
- Services: telegram, gbp (OAuth + posts + review reply), pubsub payload parse; repository for reviews
- Reuse Fernet-style token encryption pattern from MP for GBP refresh/access tokens
- Idempotency on `review_id` from Google

## Rollback

Disable webhooks in GCP/Telegram; redeploy previous image; Alembic downgrade review/OAuth tables. No data dependency from Studio Ops.

## Survey

See `exploration.md` (Q1–Q13 closed).

## Affected modules

- Backend: new `marketing` router/services/models; `requirements.txt`; env examples
- Frontend: minimal admin OAuth connect UI (Settings or dedicated entry)
- Deploy/docs: Traefik already HTTPS; Pub/Sub push URL; secrets
- OpenSpec: new domain + platform/deployment deltas
