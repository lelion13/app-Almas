# Tasks: studio-activities-rooms-edit

## Phase 1: Backend data & API

- [x] 1.1 Alembic `011_activity_rooms`: table `studio_activity_rooms` (activity_id, room_id, unique)
- [x] 1.2 Model `StudioActivityRoom` + export in `models/__init__.py` / alembic env
- [x] 1.3 Schemas: `room_ids` on ActivityCreate (≥1), ActivityPatch (optional ≥1), ActivityResponse
- [x] 1.4 Service: create/update activity with replace-set junction; reject empty; block unlink if active series
- [x] 1.5 Service: `create_series` — room MUST be linked to activity; inactive activity rejected
- [x] 1.6 Router: create/patch return `room_ids`; list activities include `room_ids`

## Phase 2: Frontend Actividades + Series

- [x] 2.1 Create form: room checkboxes grouped by sede (active rooms only)
- [x] 2.2 List: show rooms summary; **Editar** (teal) + **Eliminar** (soft DELETE)
- [x] 2.3 Modal Editar: name, level, duration, rooms, active; errors inside modal
- [x] 2.4 Series: activity select = active only; room select = site ∩ activity.room_ids

## Phase 3: Tests & docs

- [x] 3.1 Unit tests: activity room replace; unlink blocked; series room mismatch
- [x] 3.2 Update `docs/studio-ops-lessons.md`, `runbook.md`, `vps-deploy.md` (head **011**)
- [x] 3.3 Mark tasks; verify-report when apply done

## Dependencies
- 1 before 2 and 3
- 2 parallel ok with 3.1 after 1
- Docs after apply
