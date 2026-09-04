# Archive report: studio-schedule-pause

**Date:** 2026-09-04  
**Archived to:** `openspec/changes/archive/2026-09-04-studio-schedule-pause/`

## Specs synced

| Domain | Action | Details |
|--------|--------|---------|
| studio-scheduling | Updated | ADDED Schedule stack pause; MODIFIED Recurring series (suspended while paused); MODIFIED Instructors (agenda 410 + stub) |
| studio-packs | Updated | ADDED Packs stack pause |
| studio-students | Updated | ADDED Booking and waitlist pause |
| platform | Updated | ADDED Studio schedule pause flag |

## Implementation summary

- Flag `STUDIO_SCHEDULE_PAUSED` (default true) → `require_schedule_active` → 410 on series/sessions/packs/book/waitlist/attendance/instructor/me/*
- Estudio UI: catalog tabs only; alumno/instructor reconstruction stubs
- No table drops; rollback = set flag false + redeploy

## Verify

- pytest studio_ops: 21 passed
- npm run build: OK

## SDD cycle complete
Ready for next change. Operator: set `STUDIO_SCHEDULE_PAUSED=true` on VPS if not already.
