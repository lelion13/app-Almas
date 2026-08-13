# Design: studio-activities-rooms-edit

## Technical Approach

Add M2M `studio_activity_rooms`, extend activity create/patch/response with `room_ids`, enforce series room ∈ activity rooms, and mirror Salones UI (list actions + edit modal) on Actividades. Alembic **011**.

## Architecture Decisions

| Decision | Choice | Rejected | Rationale |
|----------|--------|----------|-----------|
| Link model | Junction table | Single `room_id` FK | User needs 1+ rooms across sites |
| Write semantics | Full replace of `room_ids` on POST/PATCH | Incremental add/remove endpoints | Matches room hours replace pattern; simpler UI |
| Delete | Soft via existing DELETE | Hard DELETE | Series/sessions FK; Salones pattern |
| Existing data | Empty junction after 011 | Guess backfill | Safer; admin assigns deliberately |
| Series filter | UI ∩ + backend 422 | UI-only | Backend is source of truth |

## Data Flow

```
UI Actividades create/edit
  → POST/PATCH { name, level, duration, room_ids[], active? }
  → service: validate rooms exist/active; replace junction; save activity

UI Series create
  → room picker = site ∩ activity.room_ids (active activities only)
  → POST series → service: room in activity rooms + hours + overlap
```

## File Changes

| File | Action |
|------|--------|
| `backend/alembic/versions/011_activity_rooms.py` | Create |
| `backend/app/models/studio.py` | Add `StudioActivityRoom` |
| `backend/app/models/__init__.py` | Export model |
| `backend/app/schemas/studio.py` | `room_ids` on create/patch/response |
| `backend/app/services/studio_service.py` | create/update activity + junction; series room check |
| `backend/app/api/routers/studio.py` | Wire create/patch; list includes room_ids |
| `frontend/src/pages/StudioAdminPage.tsx` | Actividades UI + Series filter |
| `docs/studio-ops-lessons.md`, `docs/runbook.md`, `docs/vps-deploy.md` | Head 011 + activities note |

## Interfaces / Contracts

```python
# ActivityCreate / ActivityPatch
room_ids: list[UUID]  # create: min_length=1; patch: if set, min_length=1

# ActivityResponse
room_ids: list[UUID]
```

Replace set on write: delete junction rows for activity, insert new pairs. Before remove: if active `ClassSeries` for `(activity_id, room_id)`, 422.

`create_series`: after loading activity, require `values["room_id"]` in linked rooms (or 422). Activity must be active for new series (existing check via picker; enforce in service if missing).

## Testing Strategy

| Layer | What |
|-------|------|
| Unit/service | Replace rooms; unlink blocked by series; series room mismatch |
| Manual | Create with rooms; Editar; Eliminar; Series picker filter |

## Migration / Rollout

`011` creates empty junction. Prod activities need admin edit before new series. No feature flag.

## Open Questions

None — locks 1–8 confirmed.
