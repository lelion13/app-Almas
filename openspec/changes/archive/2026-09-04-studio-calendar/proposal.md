# Proposal: studio-calendar

## Intent

Estudio admin **Calendario** (week view): availability from room open hours + capacity + activity duration, cascade filters, assign instructor per slot (persists as `ClassSeries`), show assignment on reopen. Booking for alumnos later.

## Scope

**In**
- Tab Calendario (week navigation Mon–Sun)
- Cascade filters: site → rooms; activity limits rooms via `room_ids`
- `GET /calendar/availability` + `POST /calendar/schedule` (not blocked by pause)
- Holidays attenuated; slot tiling by activity duration
- Overlay active series; modal instructor filter by `activity_ids`; upsert on same slot

**Out**
- Alumno booking from calendar; packs; month view
- Restoring Series/Sesiones admin tabs; expand-sessions UI

## Approach

Catalog tiling + series overlay in `studio_service`; thin router; `StudioCalendarPanel`. No Alembic migration.

## Rollback

Remove tab + calendar endpoints; series rows created via calendar remain until deactivated manually. Pause flag unchanged.

## Affected modules

- `backend/app/schemas/studio.py`, `services/studio_service.py`, `api/routers/studio.py`
- `frontend/src/components/StudioCalendarPanel.tsx`, `pages/StudioAdminPage.tsx`
- Specs: `studio-scheduling`, `platform`
- Docs: `studio-ops-lessons.md`, `runbook.md`
