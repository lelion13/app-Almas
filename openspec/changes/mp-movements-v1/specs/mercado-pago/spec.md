# Delta: Mercado Pago — Movimientos (Account Money)

## MODIFIED Requirements

### Requirement: Conciliación UI structure

The system MUST expose a primary nav item **Conciliación** (admin only) leading to a single page with two tabs:
1. **Cuentas Mercado Pago**
2. **Movimientos** (replaces former **Ingresos**)

#### Scenario: Two tabs present
- **GIVEN** an admin on Conciliación
- **WHEN** the page renders
- **THEN** both tabs Cuentas Mercado Pago and Movimientos MUST be available
- **AND** there MUST NOT be an Ingresos tab powered by Payments search

### Requirement: On-demand income fetch (no persistence)

**REMOVED / REPLACED** by **On-demand account movements fetch** below. The former Payments-search-based income requirement MUST no longer be the Conciliación primary fetch.

### Requirement: Explicit non-goals (V1)

Update non-goals: fetching MP withdrawals/egresos is **in scope** via Account Money movements. Remaining non-goals:
- link or reconcile MP movements with SigueFit lines or monthly closings
- auto-match
- ingest MP webhooks
- allow staff to manage Conciliación
- paste manual Access Tokens instead of OAuth
- persist movement rows or report files in the Almas database

## ADDED Requirements

### Requirement: On-demand account movements fetch (no persistence)

The system MUST allow admin to fetch **account money movements** for **one** active connected account and a from/to datetime range. The inclusive span MUST NOT exceed **60 days**.

The system MUST obtain movements via Mercado Pago **Account Money Report** APIs (generate → wait until processed → download CSV → parse), using the account’s OAuth access token (refreshing if needed). The system MUST return movement DTOs to the client and MUST NOT persist report files or movement rows in the database.

While waiting for the report, the UI MUST show a blocking loading state (spinner + legend). The backend MAY block the HTTP request until the report is ready or until a configured timeout, returning an error if generation fails or times out.

Each movement DTO MUST include at least: source id, transaction date, transaction type (raw), human-readable type label (Spanish), bucket (`ingreso` | `egreso` | `otro`), amount, currency, description (when present), external reference (when present).

Bucket mapping MUST be:
- `ingreso`: `SETTLEMENT`
- `egreso`: `REFUND`, `CHARGEBACK`, `WITHDRAWAL`, `PAYOUT`
- `otro`: `DISPUTE`, `WITHDRAWAL_CANCEL`, and unknown types

The UI MUST provide filters:
- bucket: Todos | Ingresos | Egresos
- transaction type (extra filter; Spanish labels)
- optional currency and free-text search

Filters MAY be applied client-side after the full response arrives.

#### Scenario: Valid range fetch
- **GIVEN** an active connected account and a from/to range of at most 60 days
- **WHEN** admin requests movements
- **THEN** the system MUST generate/download the Account Money report for that range and return movement DTOs
- **AND** MUST NOT write those movements to durable storage

#### Scenario: Range too long
- **GIVEN** from/to spanning more than 60 days
- **WHEN** movements are requested
- **THEN** the response MUST be `422`

#### Scenario: Withdrawal appears as egreso
- **GIVEN** a report row with `TRANSACTION_TYPE=WITHDRAWAL`
- **WHEN** movements are returned
- **THEN** the DTO bucket MUST be `egreso` and the type label MUST indicate retiro bancario

#### Scenario: Loading UX
- **GIVEN** admin clicks Consultar
- **WHEN** the report is still generating
- **THEN** the UI MUST show a spinner and a legend indicating report generation is in progress

### Requirement: Payments search not primary

The Conciliación UI MUST NOT call `/payments/search` as its primary movements source. The Payments search endpoint MAY be removed from the public API in this change.

#### Scenario: No Ingresos payments table
- **GIVEN** an admin on Conciliación Movimientos
- **WHEN** they consult a date range
- **THEN** results MUST come from Account Money movements, not payment search cobros-only list
