# Tasks: mp-movements-v1

## Phase 1: Config

- [x] 1.1 Add `MP_REPORT_POLL_INTERVAL_SECONDS`, `MP_REPORT_POLL_TIMEOUT_SECONDS` to config + `.env.example` / `.env.prod.example`

## Phase 2: Backend movements

- [x] 2.1 Add Movement DTOs / request-response schemas; remove Payment DTOs if unused
- [x] 2.2 Implement `mp_account_money_service.py` (config ensure, generate, poll, download, CSV parse, bucket map)
- [x] 2.3 Add router `POST /accounts/{id}/movements/search`; remove payments/search
- [x] 2.4 Delete or stop exporting `mp_payments_service` payments path

## Phase 3: Tests

- [x] 3.1 Unit tests: range, bucket/labels, CSV parse sample
- [x] 3.2 Run pytest (5 passed)

## Phase 4: Frontend

- [x] 4.1 Replace Ingresos tab with Movimientos + loading spinner/legend
- [x] 4.2 Filters Todos/Ingresos/Egresos + tipo + currency/text; update table columns

## Phase 5: Docs

- [x] 5.1 Update runbook + mp-conciliation-lessons (movimientos / Account Money)
- [x] 5.2 Mark tasks complete; update change state to applied
