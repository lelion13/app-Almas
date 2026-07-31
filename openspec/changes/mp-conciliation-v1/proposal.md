# Proposal: mp-conciliation-v1

## Summary
Introduce an admin-only **Conciliación** module to connect multiple Mercado Pago seller accounts via OAuth and query payment incomes for a chosen date range (max 60 days), displaying results in the UI without persisting payment rows or matching them to SigueFit closings.

## Motivation
Operators need visibility of real Mercado Pago inflows per connected account before building reconciliation against SigueFit. V1 delivers account connectivity and read-only income inspection as a foundation for later matching work.

## Scope

### In scope
- Nav item **Conciliación** (admin only) → single page with tabs **Cuentas Mercado Pago** and **Ingresos**
- Persist MP **accounts** (internal name, MP user id, active flag, encrypted access/refresh tokens, token metadata)
- OAuth authorization-code flow (one Almas MP app; many sellers); callback; refresh-token renewal when calling MP
- On-demand payments fetch for one account + from/to (≤ 60 days); return all statuses; UI-side filters
- Income table columns: payment id, date, amount, currency, status, description, payer reference
- Encrypt tokens at rest with env encryption key
- Document env vars and redirect URI for local + `almas.lionapp.cloud` (user deploys via git push)

### Out of scope
- Linking / reconciling with SigueFit or monthly closings
- Auto-match
- Webhooks / realtime sync
- Persisting payment/income lines
- MP egresos / withdrawals
- Staff access to Conciliación
- Manual Access Token paste (OAuth only)

## Approach
1. **Backend**: new domain `mercado-pago` — models/migration for accounts; Fernet (or equivalent) crypto helper; OAuth start/callback/refresh; payments search proxy; AdminOnly routes under `/api/v1/mp/...`
2. **Frontend**: route `/conciliacion` (admin guard); tabs Accounts + Incomes; OAuth launch + return handling; date range validation (≤ 60 days); client filters on status/currency/etc.
3. **Config/deploy**: `MP_CLIENT_ID`, `MP_CLIENT_SECRET`, `MP_REDIRECT_URI`, `MP_TOKEN_ENCRYPTION_KEY`, `MP_API_BASE_URL`; update `.env.example` / `.env.prod.example` / `docs/vps-deploy.md`
4. **SDD**: delta specs for `mercado-pago`, `platform`, `deployment`; design with OAuth sequence; tasks for implement/verify

## Affected areas
- `backend/app` (models, alembic, routers, services, schemas, config)
- `frontend/src` (AppShell nav, routes, new Conciliación page)
- `openspec/specs` (`mercado-pago` new; `platform`, `deployment` deltas)
- Env examples and deploy docs

## Rollback plan
- Feature-flag optional; otherwise revert deploy commit / image tags
- Drop new Alembic revision if needed (accounts table only; no payment history to lose)
- Revoke redirect URI in MP app if abandoning OAuth
- Encryption key loss makes stored tokens unreadable → force re-OAuth (document)

## Open points for design (non-blocking)
- Exact MP payments search endpoint + pagination strategy
- Frontend vs backend-owned OAuth callback URL (recommend backend callback for secret safety)
- Whether PKCE is mandatory for the chosen MP app type (prefer enable)

## Success criteria
- Admin can connect ≥2 seller accounts via OAuth, rename, and deactivate
- Admin can fetch incomes for one account within ≤60 days and filter in UI
- Tokens never returned in plaintext to the client; never logged
- Staff cannot access Conciliación UI or MP APIs
- No payment rows stored in DB
