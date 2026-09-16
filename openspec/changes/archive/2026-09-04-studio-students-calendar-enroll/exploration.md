# Exploration: studio-students-calendar-enroll

**Change**: `studio-students-calendar-enroll`  
**Date**: 2026-09-04  
**Status**: Survey CLOSED — ready for proposal/specs

## Intent

1. Unificar email de contacto y acceso (alumnos)
2. Crear alumno: email/password vacíos y opcionales (visibles)
3. Grilla alumnos: Editar + Eliminar a la derecha (como instructores)
4. Calendario: en franja con instructor, asignar alumno si hay cupo (puntual, sin pack, API carve-out)

## Current State

- Students: separate `email` + `login_email`/`password`; create via simple `ProfileSection`; list without edit actions
- Instructors: already single `email` + optional password + edit/delete row UI
- Calendar: instructor assign via `/calendar/schedule`; no student enroll; packs/booking paused (410)

## Survey (CLOSED)

| Q | Decision |
|---|----------|
| Q1 | **A** Un solo campo **Email** (contacto = login cuando hay acceso), como instructores |
| Q2 | **B** Email y contraseña visibles, vacíos y opcionales al crear |
| Q3 | **A** Editar (modal) + Eliminar soft a la derecha |
| Q4 | **A** Reserva **puntual** de esa fecha del calendario |
| Q5 | **A** Cupo = capacidad − ya asignados; **sin** pack/crédito |
| Q6 | **A** API calendario nueva, exenta del pause |

## Recommendation

Align student email/login with instructor pattern. Rebuild Alumnos UI (create + row actions). Calendar modal (when series/instructor assigned): enroll student for that date if `booked < capacity`; persist via calendar carve-out endpoint (ensure session exists or book against series occurrence without pack).

## Risks

- Materialized `ClassSession` may not exist for the date while expand is paused — need create-on-demand session or booking keyed by series+date
- Existing students with divergent `email` vs `login_email` need migration/align rule
- Booking table may still expect `pack_id` — schema/service change for pack-optional admin enroll

## Ready for Proposal

Yes
