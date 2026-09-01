# Proposal: studio-instructors-edit

## Intent

Complete the Estudio → **Instructores** admin experience: list with row actions (Editar / Eliminar) matching Salones and Actividades, and persist a catalog-only link between each instructor and zero or more activities.

Backend CRUD endpoints exist but the UI is create-only; activity association does not exist in the database.

## Scope

### In Scope
- DB: `studio_instructor_activities` (M2M, unique pair); Alembic **013**
- API: create/patch accept `activity_ids` (0+); list/response include `activity_ids`
- API: `InstructorPatch` supports profile fields + optional `login_email`/`password` pair on edit
- Service: replace-set of `activity_ids` on write; validate activity ids exist/active only (no series/session checks)
- UI Instructores: create form with activity checkboxes; list with **Editar** + **Eliminar** (right-aligned, same as Salones/Actividades)
- Modal Editar: name, contact email, phone, activities, active, optional login credentials; errors inside modal
- Eliminar: existing `DELETE` (soft `active=false`); inactive rows remain visible; reactivation via Editar
- Series form: **unchanged** — any instructor remains selectable (catalog only)

### Out of Scope
- Filtering series instructor picker by activity
- Validating activity unlink against existing series/sessions
- Teachers domain (`/teachers`) sync or merge
- Staff access (admin-only remains)
- Hard-delete of instructors or junction rows

## Approach

Mirror `studio_activity_rooms` pattern: junction table + replace-set on write. Extend instructor create/patch/response with `activity_ids`. Replace `ProfileSection` with a dedicated Instructores section matching Actividades UX. Soft-delete unchanged.

## Affected Areas

| Area | Impact |
|------|--------|
| `backend/alembic/versions/013_instructor_activities.py` | New |
| `backend/app/models/studio.py` | New `StudioInstructorActivity` |
| `backend/app/schemas/studio.py` | `activity_ids`, `InstructorPatch` |
| `backend/app/services/studio_service.py` | Junction replace + instructor create/update helpers |
| `backend/app/api/routers/studio.py` | Wire list/create/patch responses |
| `frontend/src/pages/StudioAdminPage.tsx` | Instructores UI |
| `openspec/specs/studio-scheduling/spec.md` | Delta |
| `openspec/specs/deployment/spec.md` | Delta (head **013**) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Existing instructors have zero activities after migration | High | Expected; catalog optional |
| Login edit on instructor with existing user | Med | Reuse create pair rule; conflict check on email change |
| Confusion with Teachers module | Low | Out of scope; no UI cross-link |

## Rollback Plan

Revert UI and backend deploy. `alembic downgrade 012` only if junction unused. Do not drop junction in prod without backup.

## Dependencies

- Alembic head **012** (`system_backups`). This change is **013**.
- Active activities list for checkbox picker (existing endpoint).

## Success Criteria

- [ ] Create instructor with 0 or more activities → persisted `activity_ids`
- [ ] List shows all instructors (active + inactive) with activity names/ids
- [ ] Editar updates fields, activities, active, and optional login; errors stay in modal
- [ ] Eliminar sets `active=false`; row remains listed as inactive
- [ ] Reactivate via Editar (`active=true`)
- [ ] Series instructor picker unchanged (no activity filter)
- [ ] Removing an activity from an instructor with existing series still saves
