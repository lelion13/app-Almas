# Delta: studio-aranceles (final / archive)

## ADDED / MODIFIED (as shipped)

### Requirement: Packs removed
Drop packs DB + APIs; `booking.abono_id`; alembic env MUST import arancel models only.

### Requirement: Arancel catalog
Admin CRUD: name, price, classes_per_week, activity_ids, active; price snapshot on abono.

### Requirement: Student abono
Rolling month (same day +1); ≤N series of arancel activities; no activity overlap across active abonos.

### Requirement: Weekday convention
Series/calendar weekday **0=Sunday**. Abono UI MUST label accordingly.

### Requirement: Materialize period bookings
Saving series creates calendar bookings for period dates; create covers them by default.

### Requirement: Turn coverage UI
Series ≠ turnos. Eligible checkboxes: all ticked if none covered; else restore covered. Unchecked = on calendar, not covered.

### Requirement: Partial payments / annul / roles / pause / UI
As in main `studio-aranceles` spec.

## Lessons (post-survey)

| Issue | Fix |
|-------|-----|
| Deploy crash `FixedEnrollment` import | Update `alembic/env.py` with models |
| Abono showed Mar instead of Lun | Labels used Mon=0; calendar is Sun=0 |
| Series chosen but student missing on calendar | Materialize bookings on series save |
| Eligible all unchecked felt wrong | Default all ticked when none covered |
| Q8 “mark to cover” vs UX | Shipped: all covered by default; destild exceptions |
