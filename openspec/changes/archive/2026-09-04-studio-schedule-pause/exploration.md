# Exploration: studio-schedule-pause

## Intent
Pausar el stack de agenda/créditos en Estudio (Series, Sesiones, Productos, Paquetes) para reconstruir turnos desde cero, sin perder el catálogo sólido.

## Current spine
```
Catálogo (sedes → salones/horarios → actividades → instructores/alumnos)
  → Series → Sesiones (expand + holidays)
  → Packs → Bookings / Waitlist / Fixed / Attendance
```

## Discovery locks

| # | Decisión |
|---|----------|
| 1 | Pausar, no mejorar Series/Sesiones/Paquetes in-place |
| 2 | Nivel **A+B**: ocultar UI + congelar APIs de mutación/lectura operativa del stack |
| 3 | Conservar catálogo + feriados (CRUD) + auditoría |
| 4 | Portales alumno/instructor: stub “en reconstrucción” (no 500) |
| 5 | **No** dropear tablas ni migraciones (C diferido) |
| 6 | Rebuild futuro = un stack (schedule + entitlement + book), no tres features aisladas |

## What stays foundation
Sites, rooms (+hours, space share), activities (+rooms), instructors (+activities, email único), students (+login), holidays CRUD, audit.

## What pauses
Series, expand-sessions, sessions/mass-cancel, pack-products, student-packs, transfer-credits, fixed-enrollments, bookings, waitlist, attendance, instructor agenda data, alumno book/pack UI.

## Soft couplings (leave code; harmless with empty data)
Room move / hours / activity unlink still reference active series — OK until schema drop.

## Risk of UI-only (A alone)
APIs remain callable; portals empty/broken. Prefer A+B in one change.

## Ready for propose
Yes — change name `studio-schedule-pause`.
