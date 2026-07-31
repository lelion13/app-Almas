# Monthly Closings

## Purpose
Manage monthly accounting closings (one per year/month), their lifecycle (`draft` / `finalized`), notes, and income/expense summaries used by staff and admin.

## Requirements

### Requirement: Unique closing per year and month

The system MUST allow creating a closing with `{year, month}` that starts in status `draft`. The pair `(year, month)` MUST be unique. Duplicate creation MUST return `409`.

#### Scenario: Create closing
- **Given** authenticated staff or admin
- **When** `POST /api/v1/closings` with a new year/month
- **Then** the closing MUST be created with status `draft`

#### Scenario: Duplicate year/month
- **Given** a closing already exists for that year/month
- **When** create is attempted again
- **Then** the response MUST be `409`

### Requirement: List and detail

The system MUST expose:
- `GET /api/v1/closings` (optional filters: year, month, status)
- `GET /api/v1/closings/{id}`

Access MUST require StaffOrAdmin.

### Requirement: Draft vs finalized lifecycle

While status is `draft`, the system MUST allow imports (SigueFit and expense Excel), deletion of import batches, and mutations of manual expenses (subject to those domains’ rules).

While status is `finalized`, the system MUST reject new imports, batch deletes, and manual expense mutations with a client error (`400`). Summaries and reads MUST remain available.

#### Scenario: Finalize closing
- **Given** a draft closing and authenticated staff or admin
- **When** `PATCH /api/v1/closings/{id}` sets `status` to `finalized`
- **Then** further import uploads MUST be rejected

#### Scenario: Reopen requires admin
- **Given** a finalized closing
- **When** a `staff` user PATCHes `status` back to `draft`
- **Then** the response MUST be `403`
- **When** an `admin` user performs the same PATCH
- **Then** the closing MUST return to `draft`

### Requirement: Notes and delete

`PATCH` MUST allow updating `notes` (and status per rules above). `DELETE /api/v1/closings/{id}` MUST succeed only for `draft` closings. Frontend MAY omit delete UI; API behavior remains in scope.

### Requirement: Income summaries

For a closing, over all SigueFit `imported_payment_lines`, the system MUST provide:

| Endpoint | Behavior |
|----------|----------|
| `.../summary/payment-categories` | `SUM(amount)`, `COUNT(*)` by normalized `payment_category` |
| `.../summary/payment-methods` | same by `payment_method` |
| `.../summary/overview` | total sum; sum of amounts ≥ 0; sum of amounts < 0; distinct client count |

Grouping keys MUST be normalized (trim, collapse spaces, Unicode NFC) consistently with import.

### Requirement: Yoga attribution summary

`GET .../summary/yoga-attribution` MUST apply the fixed category rules in `yoga_income.py` (including export aliases). Only matching categories appear. Each item MUST include original amount, rule label, and attributed Yoga amount (2 decimal places). Response MUST include `total_yoga`. Unmatched categories MUST be omitted without error.

### Requirement: Imported expense method summary

`GET .../summary/imported-expense-methods` MUST aggregate `imported_expense_lines` by payment method (`SUM`, `COUNT`) and MUST NOT alter income overview totals.

### Requirement: Frontend surfaces

- `/` — list/create closings (`ClosingsListPage`)
- `/closings/:id` — detail with summaries, imports, expenses, finalize/reopen (`ClosingDetailPage`)
- Reopen control MUST be shown only to admin in the UI

## Related domains
- `siguefit-imports`, `expense-imports`, `manual-expenses`, `teachers`, `auth`
