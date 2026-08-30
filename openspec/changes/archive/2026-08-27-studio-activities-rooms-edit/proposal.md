# Proposal: studio-activities-rooms-edit

## Intent
Admin must attach each Estudio activity to one or more rooms, then edit or soft-delete it from the Actividades list the same way Salones uses row actions.

## Scope

### In Scope
- DB: `studio_activity_rooms` (M2M, unique pair); Alembic **011**
- API: create/patch accept `room_ids` (≥1); response includes `room_ids`
- Service: series create/update rejects room not linked to the activity
- Service: cannot remove a room that has an active series for that activity
- UI Actividades: create with room checkboxes (by sede); list with **Editar** + **Eliminar**
- Modal Editar: name, level, duration, rooms, active; errors inside modal
- Eliminar: existing `DELETE` (soft `active=false`)
- Series form: room options = selected site ∩ activity rooms

### Out of Scope
- Hard-delete of activities or junction rows that history needs
- Auto-backfill of rooms onto existing activities
- Prefill series duration from activity
- Instructor/alumno editing activities
- Packs scoped by activity

## Approach
Junction table + replace-set of `room_ids` on write. Keep activity fields as today. Soft-delete unchanged. Filter Series room picker; backend remains source of truth (`422`).

## Affected Areas

| Area | Impact |
|------|--------|
| `backend/alembic/versions/011_activity_rooms.py` | New |
| `backend/app/models/studio.py` | New `StudioActivityRoom` |
| `backend/app/schemas/studio.py` | `room_ids` on create/patch/response |
| `backend/app/services/studio_service.py` | Link set + series/room check |
| `backend/app/api/routers/studio.py` | Wire create/patch |
| `frontend/src/pages/StudioAdminPage.tsx` | Actividades + Series filter |
| `openspec/specs/studio-scheduling/spec.md` | Delta |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Existing activities have zero rooms | High | List warning; series 422 until edited |
| Unlink room used by series | Med | Reject if active series on that pair |
| Soft-delete confused with hard | Low | Copy: “se desactiva; el historial queda” |

## Rollback Plan
Revert UI; `alembic downgrade 010` only if unused. Do not drop junction in prod without backup.

## Dependencies
- Alembic head **010** (share-space). This change is **011**.
- Uncommitted rooms/hours work ships in the same later commit (user request).

## Success Criteria
- [ ] Create activity without rooms → rejected
- [ ] Create with 2+ rooms (possibly two sites) → persisted
- [ ] Editar updates fields and room set; errors stay in modal
- [ ] Eliminar sets `active=false`; row remains listed as inactiva
- [ ] Series with a room not linked to the activity → 422
- [ ] Series picker only shows compatible rooms
