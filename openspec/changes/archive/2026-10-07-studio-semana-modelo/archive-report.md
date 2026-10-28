# Archive report: studio-semana-modelo

**Date:** 2026-10-07  
**Archived to:** `openspec/changes/archive/2026-10-07-studio-semana-modelo/`

## Specs synced

| Domain | Action |
|--------|--------|
| studio-scheduling | Semana modelo grid + instructor access (expanded) |
| studio-aranceles | Student abono via `model_slot_ids`; Abono UI; pause carve-out; Estudio UI |
| deployment | Head **017** + `017` table list (already + `017 MUST create…`) |
| platform | Instructor Estudio tabs; product scope mentions semana modelo |

## Lessons merged into specs/docs

1. Grid = room hours ÷ activity duration; cupo = room.capacity
2. Clear cell (`student_ids=[]`) deletes slot; **no cascade** to abonos/calendar; `instructor_id` optional on clear
3. Abono requires prior modelo assignment; empty/foreign slots → 422
4. Save abono upserts ClassSeries from slots + materializes period bookings
5. Instructor GETs for catalog; Estudio tabs for instructor: modelo / alumnos / aranceles RO
6. Model-week APIs in schedule-pause carve-out

## Out of scope left deferred

- Student self-service moves on modelo
- Cascading delete from modelo to calendar
- Full instructor Estudio portal redesign beyond tab access
- Auto-cover of turnos created after abono save without re-opening Abonos
- Alumno self-pay / MP checkout

## SDD cycle complete

Active change cleared. Alembic head **017**.
