# Proposal: studio-students-calendar-enroll

## Intent

Improve Estudio **Alumnos** UX (unified email, create form, edit/delete grid) and allow admins to **assign a student to a calendar slot** for a specific date when an instructor is already assigned and capacity remains — without requiring packs while schedule pause is on.

## Scope

### In Scope
- Unify student contact/login into a single **Email** field (instructor-like rules)
- Create form: email + password visible, empty, optional (no autofill defaults)
- Alumnos grid: **Editar** (modal) + **Eliminar** (soft) on the right
- Calendar: on assigned slot, enroll student for **that date** if `booked < capacity`; no pack/credit
- New calendar enroll API carve-out (not 410 under `STUDIO_SCHEDULE_PAUSED`)
- Ensure session exists for that date (create-on-demand from series if needed)
- Allow booking without pack for this admin path (schema/service)

### Out of Scope
- Alumno self-service booking UI
- Restoring packs/credits for this enroll
- Series-wide / fixed enrollment from calendar
- Reopening full `/me/book` or Series tabs

## Approach

1. Align `StudentCreate`/`StudentPatch`/`StudentResponse` with single `email` + optional `password` (sync User when enabling login); migrate/align existing divergent emails where possible.
2. Rebuild Alumnos section UI like Instructores (create form + row actions + edit modal).
3. Extend calendar slot modal: list students, show remaining capacity, POST enroll → ensure `ClassSession` for series+date, create `Booking` with nullable `pack_id` (no credit).
4. Document pause carve-out next to existing calendar schedule endpoints.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/.../schemas/studio.py` | Modified | Student email contract; calendar enroll schemas |
| `backend/.../studio_service.py` | Modified | Student CRUD email; enroll + session ensure |
| `backend/.../studio.py` router | Modified | Student routes; `POST /calendar/enroll` |
| Alembic | New | `bookings.pack_id` nullable (or equivalent) |
| `StudioAdminPage` / calendar panel | Modified | Students UI; enroll in slot modal |
| `openspec/specs/studio-students`, `studio-scheduling`, `platform` | Modified | Delta then merge on archive |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Sessions missing while expand paused | High | Create session on enroll from series |
| `pack_id` NOT NULL blocks no-credit book | High | Migration + service path |
| Duplicate email vs login data | Med | Align like instructors; clear 422/409 |

## Rollback Plan

- Revert UI/API; keep migration making `pack_id` nullable (safe). Soft-delete bad bookings if needed. Pause flag unchanged.

## Dependencies

- Shipped `studio-calendar` (series on slot + overlay)
- Catalog students must exist before enroll

## Success Criteria

- [ ] Create/edit student uses one Email field; optional password enables access
- [ ] Create form does not prefill email/password
- [ ] Grid has Editar + Eliminar like instructors
- [ ] Calendar assigned slot can enroll student when capacity free; persists; shows in capacity count
- [ ] Enroll works while `STUDIO_SCHEDULE_PAUSED=true`
- [ ] Specs + docs updated; tests for email rules + enroll capacity
