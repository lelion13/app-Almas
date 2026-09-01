# Tasks: studio-instructors-edit

## Phase 1: Infrastructure

- [x] 1.1 Add Alembic `013_instructor_activities.py` (`studio_instructor_activities`, unique `(instructor_id, activity_id)`, indexes)
- [x] 1.2 Add `StudioInstructorActivity` model; register in `models/__init__.py` and `alembic/env.py`

## Phase 2: Backend

- [x] 2.1 Extend schemas: `activity_ids` on `InstructorCreate`/`InstructorResponse`; add `InstructorPatch` with optional login pair
- [x] 2.2 Implement `get_instructor_activity_ids`, `replace_instructor_activities`, `instructor_to_response` in `studio_service.py`
- [x] 2.3 Update `create_instructor` to persist `activity_ids`; add `update_instructor` (profile, activities, login upsert)
- [x] 2.4 Wire `list_instructors`, `create_instructor`, `patch_instructor` in `studio.py` to return `activity_ids` and use `InstructorPatch`
- [x] 2.5 Add pytest: empty/multiple `activity_ids`; patch login pair validation
- [x] 2.6 Sync `User.email` when contact `email` changes on instructor with `user_id`

## Phase 3: Frontend

- [x] 3.1 Replace Instructores `ProfileSection` with create form (name, email, phone, activity checkboxes, optional password)
- [x] 3.2 Add instructor list rows with **Editar** / **Eliminar** (right-aligned); activity labels + inactive badge
- [x] 3.3 Add edit modal (structured layout); errors inside modal; reactivation support
- [x] 3.4 Confirm Series instructor picker unchanged
- [x] 3.5 Unified email: remove “Email de acceso”; contact email = login when password set

## Phase 4: Documentation

- [x] 4.1 `exploration.md`, updated `proposal.md`, `design.md`, delta specs
- [x] 4.2 `verify-report.md` with manual VPS checklist
- [x] 4.3 Update `docs/runbook.md`, `docs/vps-deploy.md`, `docs/studio-ops-lessons.md` (head **013**, instructores)

## Phase 5: Verification

- [x] 5.1 `cd backend && python -m pytest`
- [x] 5.2 `cd frontend && npm run build`
- [ ] 5.3 Manual VPS (see `verify-report.md` §4)
