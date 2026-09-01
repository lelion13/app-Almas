# Proposal: studio-instructors-edit

## Intent

Complete the Estudio → **Instructores** admin experience: list with row actions (Editar / Eliminar) matching Salones and Actividades, persist a catalog-only link between each instructor and zero or more activities, and unify contact/login email in the UI.

Backend CRUD endpoints existed but the UI was create-only; activity association did not exist in the database.

## Scope

### In Scope
- DB: `studio_instructor_activities` (M2M, unique pair); Alembic **013**
- API: create/patch accept `activity_ids` (0+); list/response include `activity_ids`
- API: `InstructorPatch` supports profile fields + optional `login_email`/`password` pair on edit
- Service: replace-set of `activity_ids`; sync `User.email` when contact `email` changes and instructor has `user_id`
- UI Instructores: create form with activity checkboxes; list with **Editar** + **Eliminar** (right-aligned)
- **Single email field** in UI: contact email doubles as login email when password is supplied
- Modal Editar: structured layout (header / scroll body / footer); password optional; errors inside modal
- Eliminar: soft `active=false`; inactive rows remain visible; reactivation via Editar
- Series form: **unchanged** — any instructor remains selectable (catalog only)
- Docs: runbook, vps-deploy, studio-ops-lessons updated for head **013**

### Out of Scope
- Filtering series instructor picker by activity
- Validating activity unlink against existing series/sessions
- Teachers domain (`/teachers`) sync or merge
- Staff access (admin-only remains)
- Hard-delete of instructors or junction rows
- Separate “email de acceso” field in UI

## Approach

Mirror `studio_activity_rooms` pattern: junction table + replace-set on write. Replace `ProfileSection` with dedicated Instructores section. On create/edit, UI maps `email` → `login_email` when password is set; backend keeps User email aligned on contact email change.

## Affected Areas

| Area | Impact |
|------|--------|
| `backend/alembic/versions/013_instructor_activities.py` | New |
| `backend/app/models/studio.py` | `StudioInstructorActivity` |
| `backend/app/schemas/studio.py` | `activity_ids`, `InstructorPatch`, `InstructorResponse` |
| `backend/app/services/studio_service.py` | Junction + create/update instructor + email sync |
| `backend/app/api/routers/studio.py` | List/create/patch responses |
| `frontend/src/pages/StudioAdminPage.tsx` | Instructores UI + unified email |
| `backend/tests/test_studio_ops.py` | Schema tests |
| `docs/runbook.md`, `docs/vps-deploy.md`, `docs/studio-ops-lessons.md` | Head 013 + instructores |
| `openspec/specs/studio-scheduling/spec.md` | Delta (on archive) |
| `openspec/specs/deployment/spec.md` | Delta (on archive) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Existing instructors have zero activities after migration | High | Expected; catalog optional |
| Email change without password on instructor with login | Med | Backend syncs `User.email` from contact email |
| Confusion with Teachers module | Low | Out of scope; no UI cross-link |

## Rollback Plan

Revert UI and backend deploy. `alembic downgrade 012` only if junction unused. Do not drop junction in prod without backup.

## Dependencies

- Alembic head **012** (`system_backups`). This change is **013**.
- Active activities list for checkbox picker (existing endpoint).

## Success Criteria

- [x] Create instructor with 0 or more activities → persisted `activity_ids`
- [x] List shows all instructors (active + inactive) with activity labels
- [x] Editar updates fields, activities, active, optional password; errors in modal
- [x] Single contact email used for login when password provided
- [x] Eliminar sets `active=false`; row remains listed as inactive
- [x] Reactivate via Editar (`active=true`)
- [x] Series instructor picker unchanged (no activity filter)
- [x] Removing activity from instructor with existing series still saves
- [ ] Manual VPS verification (user in progress)
