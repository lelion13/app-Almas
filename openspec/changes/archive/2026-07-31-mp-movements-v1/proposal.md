# Proposal: Mercado Pago Movimientos (final)

## Intent
Replace Conciliación **Ingresos** (cobros-only framing) with **Movimientos**, with filters Ingresos/Egresos/tipo, for admin reconciliation prep — without SigueFit match and without persisting rows.

## Scope (as shipped)

### In Scope
- Tab **Movimientos**; endpoint `POST /api/v1/mp/accounts/{id}/movements/search`
- Fast fetch via **Payments search** (`/v1/payments/search`)
- Client filters: Todos | Ingresos | Egresos + tipo + moneda + texto
- Columns for conciliación: Documento (DNI/CUIT/CUIL), Email, Medio de pago (when MP sends them)
- Remove Payments-only “Ingresos” tab naming

### Out of Scope / deliberately dropped
- Account Money CSV report as primary Consultar (too slow in prod: ~2 min / 5 days; month timed out)
- Bank withdrawals / cash payouts in primary Consultar
- SigueFit auto-match, webhooks, staff access, persistence

## Approach (final)
Map payment statuses to movement buckets/labels; expose payer identification and payment method fields from the payment JSON when present.

## Lessons (outside original proposal)
1. Account Money Report is async CSV — unsuitable for interactive Conciliación.
2. Chunking/parallel reports still left wall-clock dominated by MP generation latency.
3. Tradeoff accepted: speed over full wallet ledger (no WITHDRAWAL in fast path).
4. Payer DNI/CUIT/email are optional from MP; UI shows "—" when missing; `external_reference` remains best for system match.

## Rollback
Revert to previous image; no DB migration required for this change.

## Success Criteria
- Admin can consult a month of cobros in seconds (not minutes)
- Filters and payer/medio columns usable for manual conciliación prep
