# Design: studio-ops-mvp

## Architecture

New **studio** bounded context alongside closings/SigueFit/MP. Same FastAPI app + React SPA; JWT `role` extended.

```
Admin UI (studio)     → /api/v1/studio/*     (AdminOnly studio)
Instructor UI         → /api/v1/studio/instructor/*
Alumno portal         → /api/v1/studio/me/*
```

Layering: routers → services → repositories → models. Pydantic at boundary.

## Data model (logical)

| Entity | Notes |
|--------|--------|
| `StudioSite` | sede |
| `StudioRoom` | salón → site, capacity |
| `StudioActivity` | catalog activity + level |
| `StudioInstructor` | profile; optional `user_id` |
| `StudioStudent` | profile; optional `user_id` |
| `ClassSeries` | recurrence rule, room, activity, instructor, capacity, duration |
| `ClassSession` | instance (date/time); status scheduled/cancelled; series FK nullable |
| `Holiday` / `SessionException` | global or site-scoped holidays; per-occurrence overrides |
| `PackProduct` | N classes, validity_days, trial flags |
| `StudentPack` | assignment; remaining; expiry; payment method/status; scope `all_sedes` \| `site_id` |
| `Booking` | student + session; status booked/cancelled; source fixed/mobile/waitlist |
| `WaitlistEntry` | ordered queue per session |
| `Attendance` | booking → presente/ausente/tarde |
| `StudioAuditLog` | actor, action, entity, payload |
| `StudioSettings` | singleton/row: no_show_deducts_credit, etc. |

**Credits:** prefer `StudentPack.remaining_credits` updated transactionally on book/cancel/no-show/transfer (simpler than full ledger for MVP); audit captures mutations. Optional `CreditLedger` if dual-write needed — start with remaining + audit.

## Auth

- Extend `User.role` allowed values: `admin`, `staff`, `instructor`, `alumno`.
- Dependencies: `AdminOnly`, `InstructorOnly`, `AlumnoOnly`, `get_current_student`, `get_current_instructor`.
- Create user: admin POST with password → bcrypt; return once in create response to admin UI.

## Booking concurrency

Use DB transaction + `SELECT … FOR UPDATE` on session row (or capacity check with unique constraint / exclusion) when creating booking. Reject if `count(booked) >= capacity`.

## Recurrence

Store RRULE-like fields (weekday + time + timezone `America/Argentina/Buenos_Aires`). Materialize sessions in a rolling window (e.g. 8–12 weeks ahead) via job or on-demand expand in service. Holidays mark instances cancelled.

## UI

- Admin nav section **Estudio** (sedes, salones, grilla, alumnos, paquetes, feriados, auditoría, config)
- Instructor: **Mi agenda** + asistencia
- Alumno: **Mis clases**, **Reservar**, **Mis paquetes**, waitlist confirms
- Mobile-first; reuse Tailwind patterns

## Migrations

Single or sequenced Alembic revisions under `005+` (current head 004). No change to closing/MP tables.

## Explicit non-goals in design

No notification worker; no Teachers FK; no MP Checkout for packs; no recepción role.

## Sequence: mobile book

```mermaid
sequenceDiagram
  participant A as Alumno
  participant API as Studio API
  participant DB as Postgres
  A->>API: POST book(session_id)
  API->>DB: lock session + check capacity + pack scope/credits
  API->>DB: insert booking; decrement remaining
  API->>DB: audit
  API-->>A: booking
```

## Testing

- Unit: credit math, overlap validation, scope checks
- API: role 403 matrix; book/cancel/waitlist confirm
- Manual: multi-sede pack scope; mass cancel; holiday
