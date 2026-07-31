# Manual Expenses

## Purpose
Record manual expenses on a monthly closing as either vendor/services or teacher hours, editable only while the closing is in `draft`.

## Requirements

### Requirement: Expense types

Manual expenses MUST use discriminated type `service` | `teacher_hours`.

- **service**: MUST require `vendor_or_teacher_name`, `expense_date`; `description` MAY be optional; `amount` MUST be > 0
- **teacher_hours**: MUST require `teacher_id` of an **active** teacher, `hours` > 0, `hourly_rate` > 0, and `amount` MUST satisfy `abs(hours * hourly_rate - amount) <= 0.02`

#### Scenario: Teacher hours mismatch
- **Given** hours×rate differs from amount by more than 0.02
- **When** create or update is attempted
- **Then** the response MUST be a validation/`400` error

#### Scenario: Inactive teacher
- **Given** `teacher_id` points to an inactive or missing teacher
- **When** create teacher_hours expense
- **Then** the response MUST be `400`

### Requirement: Closing status gate

Mutations (`POST`, `PATCH`, `DELETE`) MUST be allowed only when the parent closing is `draft`. Reads (`GET`) MUST work for draft and finalized.

### Requirement: API surface

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/api/v1/closings/{id}/expenses` | List |
| `POST` | `/api/v1/closings/{id}/expenses` | Create |
| `PATCH` | `/api/v1/expenses/{expense_id}` | Update |
| `DELETE` | `/api/v1/expenses/{expense_id}` | Delete |

Access MUST require StaffOrAdmin.

### Requirement: Frontend

Closing detail MUST support creating and deleting manual expenses. Edit via `PATCH` MAY exist only in API (UI edit OUT OF SCOPE unless a future change adds it).

## Related
- `teachers`, `monthly-closings`
