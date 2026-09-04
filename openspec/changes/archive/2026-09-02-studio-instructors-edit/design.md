# Design: studio-instructors-edit

## Technical Approach

Add M2M `studio_instructor_activities`, extend instructor create/patch/response with `activity_ids`, add `InstructorPatch`, replace Instructores `ProfileSection` with list + modal matching Actividades. Alembic **013**. Unified contact/login email in UI; backend syncs User email on contact change.

## Architecture Decisions

| Decision | Choice | Rejected | Rationale |
|----------|--------|----------|-----------|
| Link model | Junction table | JSON on instructor | Matches `studio_activity_rooms` |
| Write semantics | Full replace `activity_ids` | Incremental endpoints | Same as activities |
| Min activities | 0 allowed | Require ≥1 | User confirmed |
| Series impact | None | Filter / block unlink | Catalog only |
| Delete | Soft via DELETE | Hard DELETE | Sessions FK |
| Login UX | One email field in UI | Separate login email | User request post-apply |
| Email sync | Patch contact → User.email | UI-only | Keeps login aligned without re-password |
| Teachers | Untouched | Merge | Separate domain |

## Data Flow

```
UI create/edit
  → email (contact) + optional password
  → if password: POST/PATCH also sends login_email = email
  → service: replace activity_ids; upsert User if password; sync User.email on contact change

UI Series (unchanged)
  → instructor picker = all instructors
```

## File Changes

| File | Action |
|------|--------|
| `backend/alembic/versions/013_instructor_activities.py` | Create |
| `backend/app/models/studio.py` | `StudioInstructorActivity` |
| `backend/app/models/__init__.py`, `backend/alembic/env.py` | Register model |
| `backend/app/schemas/studio.py` | `activity_ids`, `InstructorPatch`, `InstructorResponse` |
| `backend/app/services/studio_service.py` | Junction, create/update, email sync |
| `backend/app/api/routers/studio.py` | Wire responses |
| `frontend/src/pages/StudioAdminPage.tsx` | Instructores section, ActivityPickers, modal |
| `backend/tests/test_studio_ops.py` | Instructor schema tests |
| `docs/runbook.md`, `docs/vps-deploy.md`, `docs/studio-ops-lessons.md` | Head 013, instructores |

## Interfaces / Contracts

```python
# InstructorCreate
activity_ids: list[UUID] = []

# InstructorPatch
activity_ids: list[UUID] | None = None
login_email: str | None = None  # API; UI sets = email when password present
password: str | None = None

# InstructorResponse
activity_ids: list[UUID]
```

Login rules:
- API: `login_email` + `password` must be paired (Pydantic).
- UI create: password without email → error; email + password → `login_email = email`.
- UI edit: new password requires contact email; sends `login_email = email`.
- Backend: if instructor has `user_id` and contact `email` changes, update `User.email` (409 if taken).

## Testing Strategy

| Layer | What |
|-------|------|
| Unit/schema | `InstructorCreate` empty `activity_ids`; `InstructorPatch` login pair |
| Build | `npm run build` |
| Backend | `pytest` (43 passed at apply time) |
| Manual VPS | Checklist in `verify-report.md` |

## Migration / Rollout

`013` creates empty junction. Existing instructors keep zero activities until edited. Deploy: pull images → `up -d` (entrypoint runs `alembic upgrade head`).

## Shipped UI notes

- Create: nombre + teléfono en fila; email ancho completo; contraseña opcional con hint.
- Edit modal: header fijo + body scroll + footer; grid 2 cols email/teléfono; sección contraseña separada.

## Open Questions

None.
