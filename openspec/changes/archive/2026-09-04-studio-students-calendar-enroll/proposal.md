# Proposal: studio-students-calendar-enroll (final)

## Intent

Unify student email/login UX with instructors; improve Alumnos create/grid; allow admin calendar one-off student enroll without pack while schedule pause remains.

## Shipped scope

- Single Email + optional password; empty optional on create; Editar/Eliminar grid
- `POST /calendar/enroll` + availability capacity/enrolled overlay; session on-demand
- Alembic **015**: nullable `studio_bookings.pack_id` + student email align
- Pause carve-out for enroll (+ existing calendar endpoints)

## Out of scope (still)

- Alumno self-booking; packs/credits on calendar enroll; Series tabs restore
