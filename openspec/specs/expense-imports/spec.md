# Expense Imports

## Purpose
Import expense workbooks separately from SigueFit income, with a whitelist of payment methods and draft-only batch management.

## Requirements

### Requirement: Separate storage from income

Expense imports MUST use `expense_import_batches` and `imported_expense_lines`. They MUST NOT modify SigueFit income category/method/overview aggregates.

### Requirement: Upload rules

`POST /api/v1/closings/{closing_id}/expense-imports` MUST accept `.xlsx` for StaffOrAdmin on `draft` closings.

Header detection MUST require **Importe** and **Método de Pago** or **Medio de pago** (normalized names).

Allowed payment methods after normalization (case-insensitive) MUST be exactly:
- Efectivo
- Transferencia Irene
- Transferencia Lea
- Transferencia Mercedes
- Transferencia Raquel

Rows with numeric amount but disallowed method MUST NOT be persisted; the API MAY return them in `row_errors`. Rows without amount MAY be skipped (`rows_skipped`). If zero valid rows remain, the response MUST be `422`.

#### Scenario: Whitelist rejection
- **Given** a draft closing and a row with method outside the whitelist
- **When** the file is imported
- **Then** that row MUST not appear in `imported_expense_lines`

### Requirement: Dedup among expense batches

`file_sha256` uniqueness MUST apply among expense batches for the same closing. The same physical file MAY also exist as a SigueFit income import (business responsibility to avoid conceptual duplicates).

### Requirement: List and delete

- `GET /api/v1/closings/{id}/expense-imports`
- `DELETE /api/v1/closings/{id}/expense-imports/{batch_id}` → `204` when draft; forbidden when finalized

### Requirement: Summary

`GET /api/v1/closings/{id}/summary/imported-expense-methods` MUST return `SUM(amount)` and `COUNT(*)` by canonical method across all expense lines of the closing.

### Requirement: Frontend

Closing detail MUST support expense Excel upload, batch list/delete, and display of the imported-expense methods summary.

## Related
- `docs/monthly-closings-spec.md` (expense section)
- `monthly-closings`, `manual-expenses`
