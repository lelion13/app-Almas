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

The system MUST allow admin to fetch movements for **one** active connected account and a from/to datetime range of at most **60 days**, via Mercado Pago **Payments search** (`/v1/payments/search`) — a synchronous JSON API suitable for interactive UI.

The system MUST NOT use Account Money / settlement CSV reports for the primary Consultar action (those reports are too slow for Conciliación UX).

Each movement DTO MUST include at least: source id, transaction date, transaction type, human-readable type label (Spanish), bucket (`ingreso` | `egreso` | `otro`), amount, currency, description, external reference when present.

Bucket mapping from payment status MUST be:
- `ingreso`: `approved` (label Cobro / type SETTLEMENT)
- `egreso`: `refunded`, `charged_back` (Devolución / Contracargo)
- `otro`: pending, in_process, in_mediation, rejected, cancelled, and unknown

Bank withdrawals (`WITHDRAWAL` / `PAYOUT`) are **out of scope** for this primary fetch (only available via slow Account Money reports, not used here).

UI filters: Todos | Ingresos | Egresos + type + currency/text. Filters MAY be client-side.

#### Scenario: Valid range fetch
- **GIVEN** an active connected account and a from/to range of at most 60 days
- **WHEN** admin requests movements
- **THEN** the system MUST call Payments search and return movement DTOs within a typical interactive latency
- **AND** MUST NOT write those movements to durable storage
- **AND** MUST NOT wait on Account Money report generation

#### Scenario: Range too long
- **GIVEN** from/to spanning more than 60 days
- **WHEN** movements are requested
- **THEN** the response MUST be `422`
