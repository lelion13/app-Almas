# Proposal: Mercado Pago Movimientos (Account Money)

## Intent
Replace Conciliación V1 **Ingresos** (Payments search / cobros only) with **Movimientos** from Mercado Pago’s official **Account Money Report**, so admins can see all balance-impacting operations and filter **ingresos / egresos / tipo**.

## Scope

### In Scope
- Replace UI tab **Ingresos** → **Movimientos**
- Backend: generate Account Money report, poll until ready, download CSV, map to DTOs (no DB persistence of rows)
- Client filters: **Todos | Ingresos | Egresos** + type (Cobro, Retiro, Devolución, …) + currency/text
- Blocking loading UX (spinner + legend) while report generates
- Remove primary use of `/payments/search` (delete endpoint/service or leave unused — prefer remove)
- Update OpenSpec `mercado-pago` + docs/lessons

### Out of Scope
- SigueFit / closing match
- Webhooks
- Staff access
- Persisting reports or movement rows
- Releases-only report path
- Changing OAuth account connect UX (reuse existing accounts)

## Approach
Use MP Account Money Report API (`/v1/account/settlement_report*`): ensure column config → POST generate → poll list/search → GET CSV → parse → return JSON. Classify `TRANSACTION_TYPE` into buckets for filters. Frontend waits on a single long request with modern loading state.

## Risks
- Report generation latency / timeouts
- OAuth token may lack report permissions → reconnect
- CSV separator/columns vary by seller config
- Test accounts may return empty reports (MP limitation)

## Rollback
- Revert deploy; restore Payments endpoint/UI from previous revision if needed (no DB migration expected)

## Success Criteria
- Admin can fetch movements for a connected account and date range ≤ 60 days
- Filters show ingresos and egresos (incl. withdrawals/payouts when present in report)
- No movement rows stored in DB
- Staff still blocked from Conciliación
