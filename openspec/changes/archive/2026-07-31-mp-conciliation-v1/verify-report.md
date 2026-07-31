# Verify report: mp-conciliation-v1

**Date:** 2026-07-31  
**Result:** Accepted (prod smoke OK after scopes fix)

## Verified in production (`almas.lionapp.cloud`)

- [x] Admin ve menú Conciliación
- [x] OAuth autoriza y vuelve con `code` al callback
- [x] Cuenta queda listada (tras fix `scopes` TEXT / mig `004`)
- [x] Consulta de pagos por rango funciona
- [x] Health OK

## Deferred / known gaps

- Tasks 5.2 / 5.3 (TestClient staff 403, mock token refresh)
- UI no distingue visualmente ingreso vs devolución
- Egresos/retiros no implementados (documentado)

## Lessons captured

See `docs/mp-conciliation-lessons.md` (errors + out-of-scope).

## Specs to merge on archive

- `mercado-pago` → new main spec (+ note scopes TEXT, payments = cobros)
- `platform` / `deployment` deltas → main specs
- Alembic head documented as **004**
