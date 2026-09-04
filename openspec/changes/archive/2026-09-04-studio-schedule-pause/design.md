# Design: studio-schedule-pause

## Technical Approach

Gate schedule/commerce/portal routes behind env flag `STUDIO_SCHEDULE_PAUSED` (default `true`). Hide Estudio tabs and stub alumno/instructor pages so they never hit gated APIs. No Alembic; data retained.

## Architecture Decisions

| Decision | Choice | Rejected | Rationale |
|----------|--------|----------|-----------|
| Pause depth | UI hide + API 410 | UI-only | Prevents curl/ops bypass |
| Flag default | `true` | `false` | Pause is the product intent of this change |
| HTTP code | 410 Gone | 403/503 | Explicit “gone until rebuild” |
| Schema | Keep tables | Drop now | Rebuild needs history option; rollback easy |
| Portal UX | Static stub | Keep calling APIs | Avoid 410 noise in UI |
| Settings tab | Leave `/settings` live | Gate settings | Harmless knobs; holidays/audit stay |

## Data Flow

```
Request → studio router
  → if path in PAUSED_SET and settings.studio_schedule_paused:
       raise 410 "Agenda y paquetes del Estudio están en reconstrucción."
  → else existing handler

Estudio UI → tabs without series/sessions/products/packs
Alumno/Instructor UI → stub only (no apiFetch to paused routes)
```

## File Changes

| File | Action |
|------|--------|
| `backend/app/core/config.py` | Add `studio_schedule_paused` |
| `backend/app/api/routers/studio.py` | Dependency / assert on paused routes |
| `frontend/src/pages/StudioAdminPage.tsx` | Remove paused tabs + sections; trim preload |
| `frontend/src/pages/AlumnoPortalPage.tsx` | Stub |
| `frontend/src/pages/InstructorAgendaPage.tsx` | Stub |
| `.env.example`, `.env.prod.example` | Document flag |
| `docs/studio-ops-lessons.md`, `docs/runbook.md` | Pause notes |
| `backend/tests/test_studio_ops.py` | Gate behavior test if lightweight |

## Paused route set

- `/series*`, `/expand-sessions`, `/sessions*`
- `/pack-products*`, `/student-packs*`, `/transfer-credits`
- `/fixed-enrollments`, `/bookings/*/cancel`, `/waitlist*`, `/attendance`
- `/instructor/*`, `/me/*` (packs, sessions, book, bookings, waitlist)

## Live route set (unchanged)

sites, rooms (+hours), activities, instructors, students, holidays, settings, audit.

## Testing Strategy

- pytest: pause flag blocks a representative paused route; catalog route still OK
- `npm run build`
- Manual: Estudio tabs; alumno/instructor stub; curl 410 on `/series`

## Rollback

Set `STUDIO_SCHEDULE_PAUSED=false` and redeploy (or revert UI). No DB undo.
