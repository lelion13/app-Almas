# Proposal: studio-schedule-pause

## Intent

Freeze Estudio’s schedule/commerce stack (Series, Sessions, Pack products, Student packs) so we can rebuild turnos from a clean design. Keep the catalog foundation (sites, rooms, activities, instructors, students) intact. Avoid patching the current series→session→pack→book chain.

## Scope

### In Scope
- Hide Estudio tabs: Series, Sesiones, Productos, Paquetes (and fixed-enrollment UI under Series)
- Keep tabs: Sedes, Salones, Actividades, Instructores, Alumnos, Feriados, Auditoría
- Stub `/mis-clases` and `/instructor` (and RoleIndex for those roles) with “en reconstrucción” — no API calls that fail
- Backend: return **410 Gone** (or equivalent gated 404) on paused studio routes for series, sessions, expand, pack-products, student-packs, transfer-credits, fixed-enrollments, bookings, waitlist, attendance, instructor portal, alumno me/* book/pack/session routes
- Docs: `studio-ops-lessons.md`, `runbook.md`; OpenSpec deltas marking schedule/packs/booking as paused
- Feature flag or single constant `STUDIO_SCHEDULE_PAUSED=true` (default on in this change) for easy rollback

### Out of Scope
- Dropping DB tables / Alembic reverse of `005` studio schedule/pack tables
- Redesign of the new turnos model (follow-up change)
- Changing catalog CRUD (sites/rooms/activities/instructors/students/holidays/audit)
- Teachers, cierres, MP, backups
- Migrating or wiping existing series/session/pack/booking rows

## Approach

Frontend-first hide + portal stubs; backend gate paused routers behind one flag so curl cannot create new schedule/commerce ops. Data and schema remain. Next change redesigns schedule+entitlement+booking as one unit.

## Affected Areas

| Area | Impact |
|------|--------|
| `frontend/src/pages/StudioAdminPage.tsx` | Remove/hide paused tabs |
| `frontend/src/pages/AlumnoPortalPage.tsx` | Stub UI |
| `frontend/src/pages/InstructorAgendaPage.tsx` | Stub UI |
| `frontend/src/App.tsx` / `AppShell.tsx` | RoleIndex / nav copy if needed |
| `backend/app/api/routers/studio.py` | Gate paused endpoints |
| `docs/studio-ops-lessons.md`, `docs/runbook.md` | Pause documented |
| `openspec/specs/studio-scheduling`, `studio-packs`, `studio-students` | Delta: paused |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Existing alumno/instructor users see blank ops | High | Explicit stub message |
| Ops still need old APIs briefly | Med | Flag to re-enable without redeploy of logic |
| Specs still describe live booking | Med | Delta specs mark MUST NOT expose until rebuild |
| Accidental schema delete later | Low | Out of scope; archive lesson |

## Rollback Plan

Set flag off / revert frontend hide + router gate; redeploy. No DB migration to undo. Rows untouched.

## Dependencies

- Catalog post-`studio-instructors-edit` (archived). Alembic head stays **014**.
- No new migration required.

## Success Criteria

- [ ] Estudio admin has no Series/Sesiones/Productos/Paquetes tabs
- [ ] Catalog tabs still create/edit as today
- [ ] Alumno and instructor see reconstrucción stub (no 500)
- [ ] Paused API routes return 410 (or gated 404) when flag on
- [ ] Catalog + holidays + audit APIs still 200
- [ ] Docs + OpenSpec deltas describe pause; no table drops
