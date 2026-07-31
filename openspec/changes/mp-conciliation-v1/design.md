# Design: mp-conciliation-v1

## Technical Approach

Implement Conciliación as a new **mercado-pago** backend domain plus an admin-only frontend page, following existing Almas patterns (`AdminOnly`, router → service → repository, `apiFetch`).

- **Accounts** are durable (Alembic table + encrypted OAuth tokens).
- **Payments** are fetched on demand from Mercado Pago and returned as DTOs; **not** stored.
- **OAuth**: authorization-code (+ PKCE) with **backend-owned callback** so `client_secret` never touches the browser.
- Maps to specs in `openspec/changes/mp-conciliation-v1/specs/mercado-pago/spec.md` and deployment/platform deltas.

## Architecture Decisions

### Decision: Backend OAuth callback

**Choice**: `GET /api/v1/mp/oauth/callback` on the backend (public to MP redirect, but validates `state`; no JWT required on callback). Start endpoint remains AdminOnly and returns `{ authorization_url }`. After success, redirect browser to `/conciliacion?oauth=ok` (or error query).

**Alternatives considered**: Frontend-only callback page that posts `code` to API.

**Rationale**: Keeps `client_secret` and code exchange server-side; Nginx already proxies `/api/` in prod so `MP_REDIRECT_URI=https://almas.lionapp.cloud/api/v1/mp/oauth/callback` works.

### Decision: PKCE + signed state

**Choice**: Generate `code_verifier` / `code_challenge` (S256) and a random `state`; store pending OAuth session in DB (or short-lived encrypted cookie/server table) keyed by `state` until callback (TTL ~10 min). Prefer small table `mp_oauth_states`.

**Alternatives considered**: State only in memory (breaks multi-worker); JWT state without PKCE.

**Rationale**: Spec requires CSRF-safe state; MP docs recommend PKCE for authorization-code.

### Decision: Encrypt tokens with Fernet

**Choice**: `cryptography.Fernet` key from `MP_TOKEN_ENCRYPTION_KEY` (url-safe base64 32-byte key). Store ciphertext in `access_token_encrypted` / `refresh_token_encrypted`. Optionally store `token_expires_at`, `token_last4`.

**Alternatives considered**: app-level Postgres pgcrypto; plaintext columns.

**Rationale**: Matches “lo más seguro posible” without operating a KMS in V1; key in env documented for prod.

### Decision: Payments via Search API, no local payment tables

**Choice**: Call Mercado Pago `GET /v1/payments/search` with seller `access_token`, `range=date_created` (or `money_release_date` if needed—default **date_created** with documented mapping to UI “Fecha”), `begin_date` / `end_date` in ISO8601, paginate (`limit`/`offset`) until exhausted or a safety cap (e.g. 50 pages). Map fields to DTO; return array to client.

**Alternatives considered**: Persist `mp_income_lines`; filter approved-only server-side.

**Rationale**: Spec: no persistence; all statuses; UI filters.

### Decision: Date range validation

**Choice**: Require `from_datetime < to_datetime` and `(to - from) <= 60 days` in Pydantic/service → `422`.

**Rationale**: Locked in discovery Q8.

### Decision: UI route and guards

**Choice**: Route `/conciliacion` inside `AppShell`; same pattern as Teachers (`me.role === "admin"` redirect). Nav label **Conciliación**. Page with local tab state: `cuentas` | `ingresos`.

**Rationale**: Spec UI structure; existing admin nav pattern.

### Decision: Token refresh lazy on use

**Choice**: Before MP API call, if `token_expires_at` is past (or 401 from MP), refresh via `grant_type=refresh_token`, re-encrypt, save, retry once.

**Rationale**: Spec token refresh scenario; avoid background jobs in V1.

## Data Flow

### OAuth connect

```
Admin UI                    Backend                         Mercado Pago
   |                           |                                |
   | POST /mp/oauth/start      |                                |
   |-------------------------->| store state+verifier           |
   |  { authorization_url }    |                                |
   |<--------------------------|                                |
   | redirect browser ----------------------------------------->|
   |                           |  GET /mp/oauth/callback?code&state
   |                           |<-------------------------------|
   |                           | POST /oauth/token              |
   |                           |------------------------------->|
   |                           | access+refresh                 |
   |                           | encrypt + upsert mp_accounts   |
   |  302 /conciliacion?oauth=ok                                |
   |<--------------------------|                                |
```

### Income fetch

```
Admin UI  --POST /mp/accounts/{id}/payments/search-->  Backend
                                                          |
                                                          |- decrypt token (refresh if needed)
                                                          |- GET /v1/payments/search (paginate)
                                                          |- map → PaymentDto[]
Admin UI  <------------- 200 PaymentDto[] ---------------|
          (client-side filters; nothing written to DB)
```

## Data model (V1)

### `mp_accounts`

| Column | Type | Notes |
|--------|------|--------|
| id | UUID PK | |
| name | str | Internal label (admin editable) |
| external_user_id | str nullable unique | MP `user_id` |
| access_token_encrypted | text | Fernet |
| refresh_token_encrypted | text | Fernet |
| token_expires_at | timestamptz nullable | |
| token_last4 | str(4) | Safe display |
| scopes | str nullable | From token response if present |
| active | bool | default true |
| created_at / updated_at | timestamptz | |

### `mp_oauth_states` (ephemeral)

| Column | Type | Notes |
|--------|------|--------|
| state | str PK | Random |
| code_verifier | str | PKCE |
| suggested_name | str nullable | Optional name from start form |
| created_at | timestamptz | TTL cleanup on read/expiry |
| created_by_user_id | UUID FK users | |

No payment/income tables in V1.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/core/config.py` | Modify | `MP_*` settings |
| `backend/app/services/mp_crypto.py` | Create | Fernet encrypt/decrypt |
| `backend/app/services/mp_oauth_service.py` | Create | start URL, callback, refresh |
| `backend/app/services/mp_payments_service.py` | Create | search + map DTOs |
| `backend/app/repositories/mp_account_repo.py` | Create | CRUD accounts + oauth states |
| `backend/app/models/mp_account.py` | Create | ORM models |
| `backend/app/models/__init__.py` | Modify | export models |
| `backend/app/schemas/mercado_pago.py` | Create | Pydantic request/response |
| `backend/app/api/routers/mercado_pago.py` | Create | routes |
| `backend/app/api/router.py` | Modify | include router |
| `backend/alembic/versions/003_mp_accounts.py` | Create | accounts + oauth_states |
| `backend/alembic/env.py` | Modify | import new models if needed |
| `backend/requirements.txt` | Modify | add `cryptography`, `httpx` (httpx already present) |
| `backend/.env.example` | Modify | MP placeholders |
| `backend/tests/test_mp_*.py` | Create | crypto, range validation, oauth state, admin auth |
| `frontend/src/pages/ConciliacionPage.tsx` | Create | tabs + accounts + incomes UI |
| `frontend/src/App.tsx` | Modify | route `/conciliacion` |
| `frontend/src/components/AppShell.tsx` | Modify | admin nav link |
| `.env.prod.example` | Modify | MP_* |
| `docs/vps-deploy.md` / `docs/runbook.md` | Modify | OAuth redirect + encryption notes |
| `openspec/config.yaml` | Modify | mention mercado-pago domain in context if needed |

## Interfaces / Contracts

### Env

```text
MP_CLIENT_ID=
MP_CLIENT_SECRET=
MP_REDIRECT_URI=http://127.0.0.1:8000/api/v1/mp/oauth/callback   # local
# prod: https://almas.lionapp.cloud/api/v1/mp/oauth/callback
MP_TOKEN_ENCRYPTION_KEY=   # Fernet.generate_key().decode()
MP_API_BASE_URL=https://api.mercadopago.com
MP_AUTH_BASE_URL=https://auth.mercadopago.com
MP_API_TIMEOUT_SECONDS=20
```

### API (all AdminOnly except callback)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/mp/oauth/start` | Body optional `{ "name": "Caja Irene" }` → `{ authorization_url }` |
| `GET` | `/api/v1/mp/oauth/callback` | MP redirect; exchange code; 302 to frontend |
| `GET` | `/api/v1/mp/accounts` | List accounts (no secrets) |
| `PATCH` | `/api/v1/mp/accounts/{id}` | `{ name?, active? }` |
| `POST` | `/api/v1/mp/accounts/{id}/payments/search` | `{ from_datetime, to_datetime }` → `{ items: PaymentDto[] }` |

### PaymentDto (response item)

```typescript
{
  id: string;
  date: string;          // ISO — prefer date_approved else date_created
  amount: string;        // decimal as string
  currency: string;
  status: string;
  description: string | null;
  payer_reference: string | null;
}
```

### Auth URL (sketch)

```text
{MP_AUTH_BASE_URL}/authorization
  ?response_type=code
  &client_id={MP_CLIENT_ID}
  &platform_id=mp
  &state={state}
  &redirect_uri={MP_REDIRECT_URI}
  &code_challenge={challenge}
  &code_challenge_method=S256
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Fernet round-trip; 60-day validation; DTO mapping from sample MP JSON | pytest |
| Unit | OAuth state mismatch rejected | pytest with mocked DB |
| Integration | Admin vs staff on `/mp/accounts` | httpx + TestClient + auth fixtures |
| Integration | payments/search refreshes token on expiry | mock httpx MP responses |
| Manual E2E | Connect sandbox/test seller, fetch range, UI filters | admin on local / prod after push |

## Migration / Rollout

1. Ship Alembic `003_mp_accounts` (name may be `003_mp_accounts` — **accounts only**, not the discarded reconciliation schema).
2. Operator sets `MP_*` in local `.env` and VPS `.env.prod`.
3. Register redirect URI in Mercado Pago application dashboard (local + prod URLs as needed).
4. User pushes to `main` → GHCR → `compose pull && up -d` on VPS.
5. No feature flag required; without `MP_*` configured, start OAuth MUST fail with clear config error.

**Rollback**: revert image tags; optionally `alembic downgrade -1` to drop accounts tables (forces re-OAuth later).

## Open Questions

Resolved in design (no longer blocking):

| Topic | Resolution |
|-------|------------|
| Callback owner | Backend |
| Payments endpoint | `/v1/payments/search` + pagination |
| Date field | Prefer `date_approved`, fallback `date_created` |
| PKCE | Enabled |

Remaining ops (not code blockers):

- Exact OAuth scopes required by the Almas MP app type (configure in MP dashboard; store whatever token returns).
- Sandbox vs production MP credentials for first connect test.

## Implementation notes for apply phase

- Reuse `AdminOnly` from `app.core.deps`.
- Prefer `httpx` AsyncClient or sync Client consistent with existing codebase style (currently sync services → sync httpx).
- Never log Authorization headers or token bodies.
- Frontend income tab: account select + datetime-local/date inputs + “Consultar” + status filter select + table.
- Deactivate = `PATCH active=false`; reconnect = new OAuth start (may upsert by `external_user_id`).
