# Studio Aranceles & Abonos

## Purpose
Catalog of fee products (aranceles) tied to activities, and student subscriptions (abonos) with rolling-month validity, partial payments, and turn coverage linked to calendar series.

## Requirements

### Requirement: Packs removed

Pack products, student packs, credit transfer, and fixed enrollments MUST NOT exist in schema or API. Booking MUST use nullable `abono_id` instead of `pack_id`.

Alembic `env.py` (and any model import lists) MUST import arancel/abono models — NOT removed pack models — or migrate entrypoint will crash on deploy.

### Requirement: Arancel catalog

Admin MUST CRUD aranceles: name, price, classes_per_week (≥1), one or more activity_ids, active. Soft delete MAY set active=false. Price changes MUST NOT alter agreed amounts on existing abonos.

### Requirement: Student abono

Admin or instructor MUST create an abono for a student with arancel, paid_on, and up to `classes_per_week` **semana modelo** slot ids where the student is already assigned for the arancel's activities. Empty slots MUST be rejected. On save the system MUST upsert ClassSeries from those slots and link abono↔slots and abono↔series. Period MUST be `paid_on` through the same calendar day next month (inclusive; clamp end-of-month). Multiple active abonos for one student MUST NOT share any activity.

**Series vs turnos:** Series are the weekly pattern derived from modelo cells. Turnos are concrete dates in the abono period for those series.

### Requirement: Weekday convention

`ClassSeries.weekday` and room-hours/calendar weekdays MUST use **0=Sunday … 6=Saturday** (same as `room_hours_weekday_from_date`). UI labels for abono series MUST use that convention. Using Monday=0 labels MUST NOT be done (it mislabels Monday as Tuesday).

### Requirement: Partial payments

Abonos MAY receive one or more payment lines. Coverage MUST run while amount_due > 0. Annul (admin or instructor) MUST clear booking links and set status annulled.

### Requirement: Materialize period bookings

When an abono's model slots / series are saved (create or update), the system MUST create calendar bookings for each occurrence of those series whose date falls in `[starts_on, ends_on]` (skip holidays, full sessions, weekday mismatch). Those bookings MUST appear on Estudio Calendario for the student.

On create (no explicit `booking_ids`), newly materialized bookings MUST be covered (`abono_id` set). On update with slot/series change and no explicit `booking_ids`, existing still-valid coverage plus newly materialized bookings MUST be covered.

### Requirement: Turn coverage UI

Eligible turnos = active bookings for the student in period ∩ chosen series. Estudio Abonos modal MUST:

- Distinguish **Series** (weekly pattern) from **Turnos elegibles** (concrete dates).
- Default checkboxes: if none covered yet, **all eligible ticked**; if some already covered, restore covered set (destilds persist after save).
- Saving with unchecked turnos MUST leave those bookings on the calendar but with `abono_id` null.

Bookings MAY also be created via calendar enroll without an abono. Linking/unlinking remains editable without changing period dates.

### Requirement: Pause carve-out

Arancel and abono APIs MUST remain available while `STUDIO_SCHEDULE_PAUSED` is true.

### Requirement: Estudio UI

Admin Estudio MUST show tab **Aranceles** for catalog CRUD and **Abonos** actions on Alumnos rows.

## Out of scope (deferred)

- Auto-cover of turnos created after abono save without re-opening Abonos
- Alumno self-pay / MP checkout
