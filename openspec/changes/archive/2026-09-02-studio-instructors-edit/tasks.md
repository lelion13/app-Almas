# Tasks: studio-instructors-edit

## Phase 1: Infrastructure

- [x] 1.1 Add Alembic `013_instructor_activities.py`
- [x] 1.2 Add `StudioInstructorActivity` model; register in `models/__init__.py` and `alembic/env.py`
- [x] 1.3 Add Alembic `014_align_instructor_emails.py` (data repair)

## Phase 2: Backend

- [x] 2.1 Schemas: `activity_ids`, `InstructorCreate`/`InstructorPatch` with `email`+`password` (no `login_email`)
- [x] 2.2 Junction helpers + `instructor_to_response` + flush on replace
- [x] 2.3 `create_instructor` / `update_instructor` with explicit email sync rules
- [x] 2.4 Wire router; `list_student_responses` / `StudentResponse` fix
- [x] 2.5 Pytest: schemas, email normalize, junction behavior

## Phase 3: Frontend

- [x] 3.1 Instructores create form + activity checkboxes
- [x] 3.2 List with Editar / Eliminar
- [x] 3.3 Edit modal; errors inside modal
- [x] 3.4 Series picker unchanged
- [x] 3.5 Single email; omit unchanged email on PATCH; password touched guard; autocomplete off

## Phase 4: Documentation

- [x] 4.1 SDD artifacts + delta specs
- [x] 4.2 verify-report + troubleshooting in studio-ops-lessons
- [x] 4.3 docs/runbook, vps-deploy, main specs sync on archive

## Phase 5: Verification

- [x] 5.1 `pytest`
- [x] 5.2 `npm run build`
- [x] 5.3 Manual VPS (operator confirmed edit works)
