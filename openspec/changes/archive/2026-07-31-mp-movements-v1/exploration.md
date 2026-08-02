# Exploration: mp-movements-v1 (archived)

## Goal (original)
All account movements + Ingreso/Egreso filters via Mercado Pago.

## Discovery locked (early)
1. Replace Ingresos tab with Movimientos  
2. Filters Todos|Ingresos|Egresos + type  
3. Blocking spinner  
4. No persistence  

## Production learning (critical)
Account Money Report was the “official” full-ledger API but **unusable** for Conciliación UX:
- 1–5 Jul ≈ 2 minutes  
- Full month → timeout  
- Chunk + parallel start helped wall-clock vs sequential but not enough  

## Final recommendation (shipped)
Use **Payments search** for Consultar. Accept missing bank withdrawals. Expose payer id/email/medio when MP provides them for manual conciliación.

## Ready for Proposal / Archive
Done — archived 2026-07-31.
