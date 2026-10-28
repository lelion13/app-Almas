# Proposal: studio-semana-modelo

## Intent

Per salon×actividad, a **semana modelo** grid of fixed weekly attendance (not consumable turnos). Source of truth for abono schedules: on payment, selected modelo cells create/update ClassSeries and materialize period bookings.

## Survey

See `exploration.md` (Q1–Q12 closed).

## Scope

### In
- Tables: model week slots + student assignments; abono ↔ slot links
- APIs: get/put grid; student slots for abono; abono uses `model_slot_ids` (replaces series picker)
- UI: tab Semana modelo; abonos modal picks modelo cells
- Alembic **017**
- Instructor+admin can edit any room/activity grid

### Out
- Student self-service moves on modelo
- Cascading delete from modelo to calendar
- Instructor-only Estudio portal redesign beyond tab access

## Rollback

Drop 017 tables; restore abono `series_ids`-only UI; previous image.
