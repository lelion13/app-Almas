# Verify report: mp-movements-v1

**Date:** 2026-07-31  
**Result:** Accepted with scope pivot

## Verified / observed in production

- [x] Account Money path too slow (~2 min for 5 days; month timeout) — **rejected for primary UX**
- [x] Payments search path returns rows quickly (after pivot)
- [x] Filters Ingresos/Egresos/tipo usable
- [x] Documento / Email / Medio columns added (null → "—" when MP omits)

## Deferred

- Bank withdrawals in UI (needs slow report or future API)
- Auto-match SigueFit
- API TestClient coverage for staff 403

## Specs to merge

`mercado-pago` main spec updated to Movimientos + Payments fast path + payer columns.
