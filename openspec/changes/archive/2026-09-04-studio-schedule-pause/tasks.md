# Tasks: studio-schedule-pause

## Phase 1: Backend gate

- [x] 1.1 Add `STUDIO_SCHEDULE_PAUSED` to `Settings` (default true) + `.env.example` / `.env.prod.example`
- [x] 1.2 Add `require_schedule_active` dependency (410 + Spanish detail)
- [x] 1.3 Apply dependency to paused routes in `studio.py`
- [x] 1.4 Pytest: paused → 410; unpaused OK

## Phase 2: Frontend

- [x] 2.1 Remove Series/Sesiones/Productos/Paquetes tabs and sections; stop preloading
- [x] 2.2 Stub `AlumnoPortalPage`
- [x] 2.3 Stub `InstructorAgendaPage`
- [x] 2.4 Soften room-hours copy about series

## Phase 3: Docs

- [x] 3.1 Update `docs/studio-ops-lessons.md` and `docs/runbook.md`
- [x] 3.2 Update `state.yaml` phase

## Phase 4: Verify

- [x] 4.1 `cd backend && python -m pytest` (studio_ops 21 passed)
- [x] 4.2 `cd frontend && npm run build`
