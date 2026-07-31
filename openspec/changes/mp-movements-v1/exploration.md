# Exploration: mp-movements-v1

## Goal
Bring **all Mercado Pago account movements** into Conciliación, with filters for **ingresos** and **egresos** (beyond V1 payments/cobros only).

## Current State (V1)
- Tab **Ingresos** calls `POST /api/v1/mp/accounts/{id}/payments/search` → MP `/v1/payments/search`.
- Shows cobros (all statuses); does **not** include bank withdrawals / cash payouts.
- No persistence of movement rows; admin-only; OAuth accounts already exist.
- Lessons: `docs/mp-conciliation-lessons.md`.

## What Mercado Pago official docs offer

There is **no** simple realtime JSON “list all movements with filters” endpoint for the seller wallet.

| API | What it returns | Ingreso / egreso? | Sync? |
|-----|-----------------|-------------------|-------|
| **Payments search** `/v1/payments/search` (already used) | Cobros / payment objects | Cobros + refunds as payment **status**; **not** retiros a banco | Sync JSON |
| **Account money report** (“Todas las transacciones” / settlement) `/v1/account/settlement_report*` | CSV of operations that **hit account money** | Yes via `TRANSACTION_TYPE` | **Async**: config → generate → list → download CSV |
| **Releases / Liquidaciones** `/v1/account/release_report*` | Released / available money report (incl. payout) | Partial (liquidity focus) | Async CSV |
| Legacy “Money withdrawn” reports | Deprecated toward Releases | — | Avoid |

### Account money — `TRANSACTION_TYPE` (official glossary)

| Type | Meaning | Suggested UI bucket |
|------|---------|---------------------|
| `SETTLEMENT` | Pago aprobado | **Ingreso** |
| `REFUND` | Devolución | **Egreso** (salida de dinero) |
| `CHARGEBACK` | Contracargo | **Egreso** |
| `DISPUTE` | Reclamo | **Otro** (o egreso si monto negativo) |
| `WITHDRAWAL` | Retiro a cuenta bancaria | **Egreso** |
| `WITHDRAWAL_CANCEL` | Retiro bancario cancelado | **Otro** / ingreso por cancelación |
| `PAYOUT` | Extracción de efectivo del disponible | **Egreso** |

Useful columns: `SOURCE_ID`, `TRANSACTION_DATE`, `TRANSACTION_AMOUNT`, `SETTLEMENT_NET_AMOUNT`, `TRANSACTION_CURRENCY`, `EXTERNAL_REFERENCE`, `DESCRIPTION`, `FEE_AMOUNT`, `IS_RELEASED`, etc.

Docs:
- [Account money intro](https://www.mercadopago.com.ar/developers/es/docs/reports/account-money/introduction)
- [Account money API](https://www.mercadopago.com.ar/developers/es/docs/reports/account-money/api)
- [Report fields / TRANSACTION_TYPE](https://www.mercadopago.com.ar/developers/es/docs/reports/account-money/report-fields)
- [Reports API overview](https://www.mercadopago.com.ar/developers/en/reference/reports/overview)

## Approaches

1. **UI-only on Payments** — classify approved vs refunded in the existing tab  
   - Pros: tiny change  
   - Cons: **no** real egresos (WITHDRAWAL/PAYOUT); does not meet “todos los movimientos”  
   - Effort: Low — **reject** for this goal

2. **Account Money Report (recommended)** — generate + poll + parse CSV; unify list; filters Ingreso / Egreso / Todos (+ tipo)  
   - Pros: official source for full balance movements; matches MP panel reports  
   - Cons: async UX (wait/poll); CSV parsing; may need report config once per seller; OAuth scopes must allow reports  
   - Effort: Medium–High

3. **Dual tabs** — keep Payments (detalle cobro) + new **Movimientos** from Account Money  
   - Pros: payments detail preserved; movements for cashflow  
   - Cons: two mental models; more UI  
   - Effort: High

4. **Releases report only** — liquidity / released money  
   - Pros: includes payouts  
   - Cons: weaker “all transactions” story than Account Money  
   - Effort: Medium — secondary if Account Money works

## Recommendation
**Approach 2** (optionally light dual: rename/repurpose Ingresos → Movimientos fed by Account Money; keep Payments as advanced/detail later or drop from primary UX).

Default product shape for this change:
- Same Conciliación page, admin-only, existing OAuth accounts
- Fetch movements for one account + date range via Account Money Report flow
- Still **no** DB persistence of rows (unless we later need cache for poll)
- Client filters: **Todos | Ingresos | Egresos** (+ optional type chips)
- Out of scope still: SigueFit match, webhooks, staff access

## Risks
- OAuth token scopes may not include Reports → reconnect / scope bump
- Report not instant → need poll + clear “generando…” UX; timeout handling
- Test accounts: MP docs say report rows may be empty
- CSV column set depends on report config; must pin required columns
- Range limits / rate limits on report generation (TBD in design; may differ from 60-day payments cap)

## Affected Areas (likely)
- `backend/app/services/mp_payments_service.py` — keep or complement
- New `mp_account_money_service.py` (generate/list/download/parse)
- `backend/app/api/routers/mercado_pago.py` — new endpoints
- `frontend/src/pages/ConciliacionPage.tsx` — filters + movements table
- `openspec/specs/mercado-pago/spec.md` — delta
- Docs / lessons

## Discovery locked
1. **UI source:** Replace V1 Payments/Ingresos with Account Money **Movimientos** (do not keep Payments tab). Remove or stop using `/payments/search` as the primary Conciliación fetch (endpoint may remain unused or be deleted in design).
2. **Filters:** Top-level **Todos | Ingresos | Egresos**, plus an **extra filter by movement type** (Spanish labels: Cobro, Retiro, Devolución, Contracargo, Reclamo, etc. mapped from `TRANSACTION_TYPE`). Table SHOULD show a human-readable Tipo column.
3. **Async UX:** Blocking wait on Consultar — modern loading state (spinner + legend e.g. “Generando reporte en Mercado Pago…”) until rows are ready or timeout/error. No background job / navigate-away-and-refresh flow in this change.
4. **Persistence:** Display-only — MUST NOT persist report files or movement rows in the DB (same as V1 payments).

## Proposed scope snapshot (updated)
- Primary fetch: **Payments search** (fast). Account Money CSV removed from Consultar (too slow for UI).
- Filters Todos | Ingresos | Egresos map cobros vs devoluciones/contracargos.
- Bank withdrawals NOT in fast path (documented tradeoff).

## Ready for Proposal
**Yes** — discovery locked; proceed to `proposal.md` when user confirms.
