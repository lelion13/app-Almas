# Design: studio-aranceles

## Data model

| Table | Role |
|-------|------|
| `studio_aranceles` | Catalog: name, price, classes_per_week, active |
| `studio_arancel_activities` | M2M arancel ↔ activity |
| `studio_abonos` | Student subscription: arancel snapshot amount, paid_on/starts_on/ends_on, status active\|annulled |
| `studio_abono_series` | Chosen series (≤ classes_per_week) |
| `studio_abono_payments` | Partial payment lines |
| `studio_bookings.abono_id` | Nullable FK; replaces `pack_id` |

## Period

`starts_on = paid_on`; `ends_on = same calendar day next month` (clamp to last day). Coverage: `starts_on ≤ session.session_date ≤ ends_on`.

## Rules

- Series must belong to arancel activities; count ≤ `classes_per_week`
- Concurrent active abonos: no shared activity between arancel activity sets
- Eligible booking: same student, booked, date in period, series in abono series, `abono_id` null (or already this abono when editing)
- Partial pay: coverage active; `amount_due = agreed_amount − sum(payments)`
- Annul: status annulled; clear booking.abono_id links
- Edit: payments, series (revalidate), booking links — not period dates
- Roles: admin arancel CRUD; admin+instructor abonos (any student)
- Not gated by `STUDIO_SCHEDULE_PAUSED`

## APIs

- `GET|POST /aranceles`, `PATCH|DELETE /aranceles/{id}` (admin)
- `GET /abonos?student_id=`, `POST /abonos`, `GET /abonos/{id}`, `PATCH /abonos/{id}`
- `POST /abonos/{id}/payments`, `POST /abonos/{id}/annul`
- `GET /abonos/{id}/eligible-bookings`

## Migration 016

Drop fixed_enrollments → clear/drop pack_id on bookings → drop student_packs → drop pack_products → create arancel tables → add `abono_id`.
