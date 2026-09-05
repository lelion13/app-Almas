# Archive report: studio-calendar

**Date:** 2026-09-04  
**Archived to:** `openspec/changes/archive/2026-09-04-studio-calendar/`

## Specs synced

| Domain | Action | Details |
|--------|--------|---------|
| studio-scheduling | Updated | ADDED Estudio calendar availability + Calendar slot instructor assignment; MODIFIED Schedule stack pause (calendar carve-out) |
| platform | Updated | MODIFIED Studio schedule pause flag (calendar carve-out scenarios) |

## Implementation summary

- `GET /api/v1/studio/calendar/availability` — week Mon–Sun; tile room hours by activity duration; overlay active series (`series_id`, instructor)
- `POST /api/v1/studio/calendar/schedule` — create or update series; instructor must be linked to activity; not gated by pause
- UI: tab Calendario, cascade filters, slot modal, assigned instructor visible
- No Alembic migration

## Verify

- pytest studio_ops: 25 passed
- npm run build: OK
- User QA: assign + reopen shows instructor

## Docs

- `docs/studio-ops-lessons.md`, `docs/runbook.md`

## SDD cycle complete
Ready for the next change.
