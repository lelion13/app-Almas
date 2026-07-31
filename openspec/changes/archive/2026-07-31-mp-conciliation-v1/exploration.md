# Exploration: mp-conciliation-v1

## Intent
Add an admin-only **Conciliación** area to connect multiple Mercado Pago seller accounts via OAuth and on-demand fetch payments for a date range (display only; no persistence of payment rows; no match to SigueFit yet).

## Decisions locked (Q&A)

| # | Topic | Decision |
|---|--------|----------|
| 1 | V1 scope | Accounts + fetch incomes only; no link to SigueFit/closings |
| 2 | Payment persistence | Do **not** persist incomes; show on screen after API fetch |
| 3 | Roles | **Admin only** |
| 4 | Account linking | **OAuth** (authorization code + refresh) |
| 5 | Payment filter | Fetch **all statuses**; filter in UI |
| 6 | UI | One page, **two tabs**: Cuentas / Ingresos |
| 7 | Account mgmt | Admin can set **internal name**, **deactivate/disconnect** |
| 8 | Date range | From/to picker; **max 60 days** |
| 9 | Table columns | id, date, amount, currency, status, description, payer reference |
| 10 | MP app | **One** Almas MP application; many sellers via OAuth |
| 11 | Token storage | **Encrypt at rest** (env key; Fernet or equivalent) |
| 12 | Out of scope | No SigueFit link, auto-match, webhooks, egresos/retiros |
| 13 | Deploy | User pushes to GitHub; GHCR → `almas.lionapp.cloud` |

## MP OAuth (docs summary)
- Authorize: `https://auth.mercadopago.com/authorization` with `client_id`, `response_type=code`, `redirect_uri`, `state` (PKCE recommended).
- Exchange: `POST https://api.mercadopago.com/oauth/token` (`grant_type=authorization_code` → `access_token` + `refresh_token`).
- Renew: same endpoint with `grant_type=refresh_token`.
- App credentials (`MP_CLIENT_ID`, `MP_CLIENT_SECRET`) and redirect URI live in env / MP app settings.
- Redirect URI must be static (e.g. `https://almas.lionapp.cloud/api/v1/mp/oauth/callback` or a frontend route that forwards code to backend).

## Payments search (V1)
- Use seller access token to call MP Payments search/list for `begin_date` / `end_date` (exact endpoint in design).
- Return normalized DTO for UI; no `mp_income_lines` table in V1.
- Persist only **account** metadata + encrypted tokens.

## Alternatives considered
| Option | Why not (V1) |
|--------|----------------|
| Manual paste Access Token | User chose OAuth |
| Persist payment lines | User deferred |
| Staff access | Admin only |
| Approved+ARS only on API | Filter in UI instead |

## Risks
- OAuth redirect / CSRF (`state`) and PKCE must be solid.
- Token refresh failure → clear admin-facing reconnect UX.
- Large ranges (up to 60d) may need pagination against MP API.
- Encryption key rotation must be documented in deploy runbook.

## Suggested domains for delta specs
- `mercado-pago` (new)
- `platform` (nav + out-of-scope update)
- `deployment` (env vars, redirect URI)
