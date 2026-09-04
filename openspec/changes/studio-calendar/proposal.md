# Proposal: studio-calendar

## Intent

Add an Estudio admin **Calendario** (week view) that shows **availability** derived from room open hours + room capacity + activity duration (catalog), filtered by cascading sede / salón / actividad. Read-only MVP; booking later.

## Scope

**In**
- New tab Calendario (week navigation)
- Cascade filters: site → rooms; activity limits rooms via `room_ids`
- Dedicated `GET` availability API (not blocked by `STUDIO_SCHEDULE_PAUSED`)
- Holidays: day visible, attenuated / marked
- Slot tiling: within each open window, consecutive slots of `activity.default_duration_minutes`

**Out**
- Booking, series CRUD, packs, instructor/alumno portals
- Month view, create/edit from calendar
- Using series/sessions as availability source

## Approach

Catalog-only computation in `studio_service` + thin router. Frontend panel with week grid. No schema migration.

## Rollback

Remove tab + endpoint; no DB changes. Pause flag unchanged.

## Affected modules

- `backend/app/schemas/studio.py`, `services/studio_service.py`, `api/routers/studio.py`
- `frontend/src/pages/StudioAdminPage.tsx` + new calendar panel component
- Specs: `studio-scheduling`, `studio-sites` (hours), `platform` (carve-out note)
- Docs: `studio-ops-lessons.md`, `runbook.md`
