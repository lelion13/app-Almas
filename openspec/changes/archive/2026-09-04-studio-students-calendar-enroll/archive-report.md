# Archive report: studio-students-calendar-enroll

**Date:** 2026-09-04  
**Archived to:** `openspec/changes/archive/2026-09-04-studio-students-calendar-enroll/`

## Specs synced

| Domain | Action | Details |
|--------|--------|---------|
| studio-students | Updated | Student profiles (unified email, UI); ADDED calendar one-off enroll; pause carve-out note |
| studio-scheduling | Updated | Pause carve-out includes enroll; capacity/enrolled on slots; ADDED student assignment UI |
| platform | Updated | Pause flag lists three calendar carve-out endpoints |
| deployment | Updated | Alembic head **015**; nullable `pack_id` + student email align |

## Implementation summary

- Students: `StudentCreate`/`Patch` like instructors; create/update services; Alumnos UI recreate
- Calendar: `booked_count`/`remaining_capacity`/`enrolled` on availability; `POST /calendar/enroll`; session create-on-demand
- Migration 015; cancel/mass-cancel safe with null pack
- Docs: `studio-ops-lessons.md`, `runbook.md`

## Beyond original survey notes

- Session ensure + holiday/cancelled guards on enroll
- Booking `source=calendar`
- Capacity on assigned slots uses **series** capacity (not only room)
- Cancel paths skip credit restore when `pack_id` is null

## Verify

- pytest 28 passed; npm build OK

## SDD cycle complete
Ready for the next change.
