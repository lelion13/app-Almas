# Mercado Pago Specification

## Purpose
Admin-only Conciliación: connect multiple Mercado Pago seller accounts via OAuth and fetch **movements** on demand for display (no row persistence; no matching to SigueFit).

Operational lessons: `docs/mp-conciliation-lessons.md`.  
Archived change: `openspec/changes/archive/2026-07-31-mp-movements-v1/`.

## Requirements

### Requirement: Admin-only Conciliación access

The system MUST restrict all Mercado Pago Conciliación APIs and UI to users with role `admin`. Staff MUST receive `403` on MP APIs and MUST NOT see the Conciliación nav item or route.

#### Scenario: Admin opens Conciliación
- **GIVEN** an authenticated admin
- **WHEN** the admin navigates to Conciliación
- **THEN** the Conciliación page MUST load

#### Scenario: Staff blocked
- **GIVEN** an authenticated staff user
- **WHEN** the staff calls any `/api/v1/mp/*` endpoint (except the public OAuth callback)
- **THEN** the response MUST be `403`

### Requirement: Conciliación UI structure

The system MUST expose a primary nav item **Conciliación** (admin only) leading to a single page with two tabs:
1. **Cuentas Mercado Pago**
2. **Movimientos** (replaces former **Ingresos**)

#### Scenario: Two tabs present
- **GIVEN** an admin on Conciliación
- **WHEN** the page renders
- **THEN** both tabs Cuentas Mercado Pago and Movimientos MUST be available

### Requirement: Persist connected MP accounts

The system MUST persist each connected seller account with at least:
- internal display name (editable by admin)
- Mercado Pago user id (when available from OAuth/token response)
- active / disconnected flag
- encrypted access token and refresh token
- non-sensitive token metadata useful for ops (e.g. token last4 or expiry timestamp) WITHOUT exposing full secrets
- OAuth `scopes` stored as unbounded text (MUST NOT truncate; column type TEXT)

The system MUST support multiple accounts linked to the same Almas Mercado Pago application.

#### Scenario: List accounts without secrets
- **GIVEN** one or more connected accounts
- **WHEN** admin lists accounts
- **THEN** the response MUST include id, name, active state, and safe metadata
- **AND** MUST NOT include plaintext access or refresh tokens

### Requirement: OAuth connect flow

Account linking MUST use Mercado Pago OAuth authorization-code flow (not manual Access Token paste). The system MUST use one Almas application (`client_id` / `client_secret` from environment). The flow MUST use a CSRF-safe `state` parameter and PKCE (`code_challenge` / `code_verifier`).

After successful callback, the system MUST store encrypted tokens and create or update the account record. The admin MUST be able to set or edit an internal name for the account.

Credentials MUST be the application **Client ID** and **Client Secret** (not Public Key / not a seller Access Token pasted as app secret).

#### Scenario: Start OAuth
- **GIVEN** an authenticated admin
- **WHEN** the admin starts connecting a Mercado Pago account
- **THEN** the system MUST return or redirect to the Mercado Pago authorization URL including client_id, redirect_uri, state, and PKCE challenge

#### Scenario: OAuth callback success
- **GIVEN** a valid authorization code and matching state
- **WHEN** the callback is processed
- **THEN** the system MUST exchange the code for tokens, encrypt and store them, and persist the account

#### Scenario: Invalid state rejected
- **GIVEN** a callback with mismatched or missing state
- **WHEN** the callback is processed
- **THEN** the system MUST reject the request and MUST NOT store tokens

### Requirement: Deactivate or disconnect accounts

The admin MUST be able to deactivate or disconnect a connected account so it cannot be used for fetches until reconnected. Soft-deactivation SHOULD be preferred.

#### Scenario: Deactivated account cannot fetch
- **GIVEN** an account marked inactive/disconnected
- **WHEN** admin requests movements for that account
- **THEN** the system MUST reject the request with a client error

### Requirement: On-demand movements via Payments search (fast path)

The system MUST allow admin to fetch movements for **one** active connected account and a from/to datetime range of at most **60 days**, using Mercado Pago **Payments search** (`GET /v1/payments/search`) — synchronous JSON suitable for interactive UI.

The system MUST NOT use Account Money / settlement CSV report generation for the primary Consultar action (those reports take minutes and timed out for month-long ranges in production).

The system MUST return movement DTOs and MUST NOT persist payment/movement rows.

Bucket mapping from payment `status`:
- `ingreso`: `approved` → type `SETTLEMENT` / label Cobro
- `egreso`: `refunded`, `charged_back` → Devolución / Contracargo
- `otro`: pending, in_process, in_mediation, rejected, cancelled, unknown

Bank withdrawals (`WITHDRAWAL` / `PAYOUT`) are **out of scope** for this primary fetch.

Movement DTOs MUST include when available from MP: source id, date, type/label, bucket, amount, currency, description, external_reference, fee_amount, **payer_email**, **payer_id_type**, **payer_id_number**, **payment_method**, **payment_type**. Payer identification fields MAY be null (MP does not always send DNI/CUIT).

UI MUST provide filters: Todos | Ingresos | Egresos, type, currency, free text (including documento/email). Table MUST show Documento, Email, and Medio columns (display "—" when absent).

#### Scenario: Valid range fetch
- **GIVEN** an active connected account and a from/to range of at most 60 days
- **WHEN** admin requests movements
- **THEN** the system MUST call Payments search and return movement DTOs
- **AND** MUST NOT write those rows to durable storage
- **AND** MUST NOT wait on Account Money report generation

#### Scenario: Range too long
- **GIVEN** from/to spanning more than 60 days
- **WHEN** movements are requested
- **THEN** the response MUST be `422`

#### Scenario: Payer document when present
- **GIVEN** a payment whose `payer.identification` includes type and number
- **WHEN** movements are returned
- **THEN** the DTO MUST expose `payer_id_type` and `payer_id_number`

### Requirement: Token encryption and secrecy

Access and refresh tokens MUST be encrypted at rest using a server-side Fernet key (`MP_TOKEN_ENCRYPTION_KEY`). Tokens MUST NEVER be logged. API list responses MUST NEVER include plaintext tokens.

### Requirement: Explicit non-goals

The system MUST NOT in this version:
- link or reconcile MP movements with SigueFit lines or monthly closings (auto-match)
- ingest MP webhooks for realtime sync
- use Account Money CSV as the primary Conciliación Consultar path
- fetch bank withdrawals/payouts in the primary Consultar path
- allow staff to manage Conciliación
- paste manual Access Tokens instead of OAuth
- persist movement rows or report files in the Almas database

## Related
- Lessons: `docs/mp-conciliation-lessons.md`
- Deploy: `docs/vps-deploy.md`, `docs/runbook.md`
- Prior archive: `openspec/changes/archive/2026-07-31-mp-conciliation-v1/`
- This change archive: `openspec/changes/archive/2026-07-31-mp-movements-v1/`
