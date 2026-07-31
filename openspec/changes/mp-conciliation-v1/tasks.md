# Tasks: mp-conciliation-v1

## Phase 1: Infrastructure / config

- [x] 1.1 Add `MP_CLIENT_ID`, `MP_CLIENT_SECRET`, `MP_REDIRECT_URI`, `MP_TOKEN_ENCRYPTION_KEY`, `MP_API_BASE_URL`, `MP_AUTH_BASE_URL`, `MP_API_TIMEOUT_SECONDS` to `backend/app/core/config.py`
- [x] 1.2 Document placeholders in `backend/.env.example` and `.env.prod.example`
- [x] 1.3 Add `cryptography` to `backend/requirements.txt` (confirm `httpx` already present)
- [x] 1.4 Create `backend/app/services/mp_crypto.py` (Fernet encrypt/decrypt + key validation helper)

## Phase 2: Data model / migration

- [x] 2.1 Create ORM models `MpAccount` and `MpOauthState` in `backend/app/models/mp_account.py`
- [x] 2.2 Export models from `backend/app/models/__init__.py` and ensure `alembic/env.py` imports them
- [x] 2.3 Add Alembic revision `003_mp_accounts.py` creating `mp_accounts` + `mp_oauth_states` (accounts only; no payment tables)
- [x] 2.4 Create `backend/app/repositories/mp_account_repo.py` (list/get/upsert account, save/consume oauth state, update tokens/name/active)

## Phase 3: Backend OAuth + payments services

- [x] 3.1 Create `backend/app/schemas/mercado_pago.py` (start body, account response, patch body, payments search request/response DTOs)
- [x] 3.2 Implement `backend/app/services/mp_oauth_service.py` (start URL with PKCE+state, callback exchange, refresh tokens, upsert account)
- [x] 3.3 Implement `backend/app/services/mp_payments_service.py` (validate ≤60 days, decrypt/refresh token, paginate `GET /v1/payments/search`, map PaymentDto)
- [x] 3.4 Ensure secrets are never logged; clear errors when MP env is missing

## Phase 4: Backend API

- [x] 4.1 Create `backend/app/api/routers/mercado_pago.py` with routes from design (`oauth/start` AdminOnly, `oauth/callback` public+state, accounts list/patch AdminOnly, payments/search AdminOnly)
- [x] 4.2 Register router in `backend/app/api/router.py`
- [x] 4.3 Callback MUST 302 to `/conciliacion?oauth=ok|error=...` after processing

## Phase 5: Backend tests

- [x] 5.1 Unit tests: Fernet round-trip; date-range >60 days → validation error; PaymentDto mapping from sample MP JSON
- [ ] 5.2 Unit/integration: invalid OAuth `state` rejected; staff gets 403 on `/mp/accounts` (deferred — no API TestClient fixtures yet)
- [ ] 5.3 Integration with mocked httpx: token refresh then successful payments search (deferred)
- [x] 5.4 Run `pytest` for new tests and fix failures (`tests/test_mp_conciliation.py` — 4 passed)

## Phase 6: Frontend Conciliación

- [x] 6.1 Add admin nav link **Conciliación** → `/conciliacion` in `AppShell.tsx` (mobile + desktop)
- [x] 6.2 Add protected route in `App.tsx`; redirect non-admin like Teachers page
- [x] 6.3 Create `ConciliacionPage.tsx` with tabs **Cuentas Mercado Pago** | **Ingresos**
- [x] 6.4 Tab Cuentas: list accounts, edit name, deactivate/activate, button “Conectar cuenta” → `POST /mp/oauth/start` then `window.location` to `authorization_url`; handle `?oauth=` query feedback
- [x] 6.5 Tab Ingresos: account select, from/to (enforce ≤60 days in UI), Consultar → `POST .../payments/search`, client filters (status/currency/text), table columns per spec
- [x] 6.6 Mobile-first layout consistent with existing Almas pages

## Phase 7: Docs / SDD hygiene

- [x] 7.1 Update `docs/vps-deploy.md` and `docs/runbook.md` with MP OAuth redirect URIs (local + `almas.lionapp.cloud`) and encryption key notes
- [x] 7.2 Note in runbook: generate Fernet key; register redirect in MP app dashboard
- [ ] 7.3 After apply/verify, archive change and merge specs into `openspec/specs/mercado-pago/` (+ platform/deployment)

## Phase 8: Verify (pre-push)

- [ ] 8.1 Manual: OAuth connect (test/sandbox seller), list/rename/deactivate account
- [ ] 8.2 Manual: fetch incomes ≤60 days; reject longer range; UI filters work; no secrets in Network responses
- [ ] 8.3 Confirm staff cannot open `/conciliacion` or call MP APIs
- [ ] 8.4 User pushes to git for GHCR → VPS deploy (out of agent apply unless requested)

## Dependencies

- Phase 2 before 3–4
- Phase 3 before 4–5
- Phase 4 before 6 (API contracts)
- Phase 7 can overlap with 6
- Phase 8 after 5–6 complete
