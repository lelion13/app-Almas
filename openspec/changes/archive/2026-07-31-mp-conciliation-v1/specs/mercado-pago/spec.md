# Mercado Pago Specification

## Purpose
Admin-only Conciliación: connect multiple Mercado Pago seller accounts via OAuth and fetch payment incomes on demand for display (no payment row persistence; no matching to SigueFit).

## Requirements

### Requirement: Admin-only Conciliación access

The system MUST restrict all Mercado Pago Conciliación APIs and UI to users with role `admin`. Staff MUST receive `403` on MP APIs and MUST NOT see the Conciliación nav item or route.

#### Scenario: Admin opens Conciliación
- **GIVEN** an authenticated admin
- **WHEN** the admin navigates to Conciliación
- **THEN** the Conciliación page MUST load

#### Scenario: Staff blocked
- **GIVEN** an authenticated staff user
- **WHEN** the staff calls any `/api/v1/mp/*` endpoint (except documented public OAuth callback if any)
- **THEN** the response MUST be `403`

### Requirement: Conciliación UI structure

The system MUST expose a primary nav item **Conciliación** (admin only) leading to a single page with two tabs:
1. **Cuentas Mercado Pago**
2. **Ingresos**

#### Scenario: Two tabs present
- **GIVEN** an admin on Conciliación
- **WHEN** the page renders
- **THEN** both tabs Cuentas Mercado Pago and Ingresos MUST be available

### Requirement: Persist connected MP accounts

The system MUST persist each connected seller account with at least:
- internal display name (editable by admin)
- Mercado Pago user id (when available from OAuth/token response)
- active / disconnected flag
- encrypted access token and refresh token
- non-sensitive token metadata useful for ops (e.g. token last4 or expiry timestamp) WITHOUT exposing full secrets

The system MUST support multiple accounts linked to the same Almas Mercado Pago application.

#### Scenario: List accounts without secrets
- **GIVEN** one or more connected accounts
- **WHEN** admin lists accounts
- **THEN** the response MUST include id, name, active state, and safe metadata
- **AND** MUST NOT include plaintext access or refresh tokens

### Requirement: OAuth connect flow

Account linking MUST use Mercado Pago OAuth authorization-code flow (not manual Access Token paste). The system MUST use one Almas application (`client_id` / `client_secret` from environment). The flow MUST use a CSRF-safe `state` parameter. The system SHOULD use PKCE when supported by the MP application configuration.

After successful callback, the system MUST store encrypted tokens and create or update the account record. The admin MUST be able to set or edit an internal name for the account.

#### Scenario: Start OAuth
- **GIVEN** an authenticated admin
- **WHEN** the admin starts connecting a Mercado Pago account
- **THEN** the system MUST return or redirect to the Mercado Pago authorization URL including client_id, redirect_uri, and state

#### Scenario: OAuth callback success
- **GIVEN** a valid authorization code and matching state
- **WHEN** the callback is processed
- **THEN** the system MUST exchange the code for tokens, encrypt and store them, and persist the account

#### Scenario: Invalid state rejected
- **GIVEN** a callback with mismatched or missing state
- **WHEN** the callback is processed
- **THEN** the system MUST reject the request and MUST NOT store tokens

### Requirement: Deactivate or disconnect accounts

The admin MUST be able to deactivate or disconnect a connected account so it cannot be used for income fetches until reconnected. Soft-deactivation SHOULD be preferred; hard delete MAY be supported if it removes encrypted tokens.

#### Scenario: Deactivated account cannot fetch
- **GIVEN** an account marked inactive/disconnected
- **WHEN** admin requests incomes for that account
- **THEN** the system MUST reject the request with a client error

### Requirement: On-demand income fetch (no persistence)

The system MUST allow admin to fetch payments for **one** active account and a from/to datetime range. The inclusive span MUST NOT exceed **60 days**. The system MUST return payment DTOs to the client and MUST NOT persist payment/income lines in the database in this version.

The fetch MUST request payments across statuses from Mercado Pago (not server-filtered to approved-only). The UI MAY filter by status, currency, or text after the response arrives.

Displayed fields MUST include at least: payment id, date (approval or creation as designed), amount, currency, status, description, payer reference.

#### Scenario: Valid range fetch
- **GIVEN** an active connected account and a from/to range of at most 60 days
- **WHEN** admin requests incomes
- **THEN** the system MUST call Mercado Pago with a valid access token (refreshing if needed) and return a list of payment DTOs
- **AND** MUST NOT write those payments to durable storage

#### Scenario: Range too long
- **GIVEN** from/to spanning more than 60 days
- **WHEN** incomes are requested
- **THEN** the response MUST be `422` (or equivalent validation error)

#### Scenario: Token refresh
- **GIVEN** an expired access token and a valid refresh token
- **WHEN** incomes are requested
- **THEN** the system MUST refresh tokens, re-encrypt and store the new pair, and complete the fetch

### Requirement: Token encryption and secrecy

Access and refresh tokens MUST be encrypted at rest using a server-side encryption key from the environment. Tokens MUST NEVER be logged. API responses to the browser MUST NEVER include plaintext tokens. Encryption key loss MUST be treated as requiring re-OAuth for affected accounts (documented in deploy notes).

#### Scenario: Secrets not in list payload
- **GIVEN** connected accounts with stored tokens
- **WHEN** `GET` accounts is called
- **THEN** no access_token or refresh_token plaintext fields MUST appear in the JSON body

### Requirement: Explicit non-goals (V1)

The system MUST NOT in this version:
- link or reconcile MP payments with SigueFit lines or monthly closings
- auto-match payments
- ingest MP webhooks for realtime sync
- fetch or manage MP withdrawals/egresos
- allow staff to manage Conciliación

## Related
- Delta updates: `platform`, `deployment` under this change
- Proposal: `openspec/changes/mp-conciliation-v1/proposal.md`
