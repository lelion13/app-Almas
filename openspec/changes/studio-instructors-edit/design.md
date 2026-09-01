# Design: studio-instructors-edit

## Technical Approach

Add M2M `studio_instructor_activities`, extend instructor create/patch/response with `activity_ids`, add `InstructorPatch` (profile + optional login pair + activities), and replace the Instructores `ProfileSection` with list actions + edit modal matching Actividades. Alembic **013**. No series/instructor filtering.

## Architecture Decisions

| Decision | Choice | Rejected | Rationale |
|----------|--------|----------|-----------|
| Link model | Junction table | JSON array on instructor | Matches `studio_activity_rooms`; queryable FK integrity |
| Write semantics | Full replace of `activity_ids` on POST/PATCH | Incremental endpoints | Same pattern as activities; simpler UI |
| Min activities | 0 allowed | Require ≥1 | User confirmed catalog optional |
| Series impact | None | Filter picker / block unlink | Catalog only; no validation on existing series |
| Delete | Soft via existing DELETE | Hard DELETE | Sessions FK; Salones/Actividades pattern |
| Login on edit | `InstructorPatch` optional pair | Create-only login | User wants edit modal to set/rotate credentials |
| Teachers | Untouched | Merge entities | Separate domain for monthly closings |

## Data Flow

```
UI Instructores create/edit
  → POST/PATCH { full_name, email?, phone?, activity_ids[], active?, login_email?, password? }
  → service: validate activities exist; replace junction; upsert optional User; save instructor

UI Series create (unchanged)
  → instructor picker = all instructors (no activity filter)
```

## File Changes

| File | Action |
|------|--------|
| `backend/alembic/versions/013_instructor_activities.py` | Create |
| `backend/app/models/studio.py` | Add `StudioInstructorActivity` |
| `backend/app/models/__init__.py`, `backend/alembic/env.py` | Export/register model |
| `backend/app/schemas/studio.py` | `activity_ids`, `InstructorPatch`, extend `InstructorResponse` |
| `backend/app/services/studio_service.py` | Junction replace; `create_instructor` / `update_instructor` |
| `backend/app/api/routers/studio.py` | List/create/patch return `activity_ids` |
| `frontend/src/pages/StudioAdminPage.tsx` | Instructores section + modals |
| `backend/tests/test_studio_ops.py` (or new) | Schema + junction replace tests |

## Interfaces / Contracts

```python
# InstructorCreate
activity_ids: list[UUID] = []  # default empty

# InstructorPatch(ProfilePatch +)
activity_ids: list[UUID] | None = None
login_email: str | None = None
password: str | None = None  # must pair with login_email when either set

# InstructorResponse
activity_ids: list[UUID]
```

Replace set on write: delete junction rows for instructor, insert new pairs. Validate each `activity_id` references an existing activity (active check optional on link — allow inactive ids only if already linked; new links should be active only).

Login patch rules:
- Both `login_email` and `password` required when either is set.
- No `user_id`: create User with role `instructor` and link.
- Has `user_id`: update email (409 if taken) and password hash.

## Testing Strategy

| Layer | What |
|-------|------|
| Unit/schema | Empty `activity_ids`; patch pair validator |
| Service | Replace activities; unlink with existing series still OK |
| Manual | Create/edit/soft-delete/reactivate; modal errors |

## Migration / Rollout

`013` creates empty junction. Existing instructors keep zero activities until edited. No feature flag.

## Open Questions

None — requirements confirmed in discovery Q&A.
