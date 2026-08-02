# Design: mp-movements-v1 (as archived)

## Final architecture

```
Admin UI Movimientos
  → POST /api/v1/mp/accounts/{id}/movements/search
      → ensure_access_token
      → GET /v1/payments/search (paginate)
      → map_payment_to_movement (bucket, payer, medio)
  ← { items: MovementDto[] }
```

No new DB tables. No Account Money report in the hot path.

## Abandoned approach (documented for learning)

Account Money Report (`/v1/account/settlement_report*`): generate → poll → CSV → parse.

| Attempt | Result |
|---------|--------|
| Single report for range | 5 days ≈ 2 min; month → timeout |
| Chunk sequential (5–7 days) | Sum of waits; still too slow |
| Chunk parallel (start all → wait all) | Better than sequential, still minutes; month unreliable |

**Decision:** remove report from Consultar; keep Payments search.

## MovementDto (shipped fields)

source_id, transaction_date, transaction_type, transaction_type_label, bucket, amount, currency, description, external_reference, fee_amount, payer_email, payer_id_type, payer_id_number, payment_method, payment_type

## Status → bucket

approved → ingreso/Cobro; refunded|charged_back → egreso; else → otro

## Config leftovers

`MP_REPORT_*` env vars MAY remain in examples from the abandoned path but are unused by the fast service. Prefer documenting Payments-only in runbook; can clean env in a later chore.

## Nginx / Traefik long timeouts

Raised for the report experiment (600s). Harmless for Payments; MAY leave as-is.
