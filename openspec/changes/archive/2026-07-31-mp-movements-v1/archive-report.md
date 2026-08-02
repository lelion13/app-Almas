# Archive report: mp-movements-v1

**Archived:** 2026-07-31  
**Path:** `openspec/changes/archive/2026-07-31-mp-movements-v1/`

## Merged into main specs

| Domain | Action |
|--------|--------|
| `mercado-pago` | Replaced with shipped behavior (Movimientos, Payments fast path, payer/medio columns, non-goals) |

## Lessons captured outside original delta

See `docs/mp-conciliation-lessons.md`, `design.md`, `proposal.md` in this archive:
- Account Money CSV unsuitable for interactive Consultar
- Parallel chunking insufficient vs MP generation latency
- Tradeoff: speed vs full wallet ledger (no withdrawals)
- Payer DNI/CUIT/email optional from MP

## Docs updated

- `docs/runbook.md`, `docs/mp-conciliation-lessons.md`
- Change proposal/design/exploration/verify/tasks/state
