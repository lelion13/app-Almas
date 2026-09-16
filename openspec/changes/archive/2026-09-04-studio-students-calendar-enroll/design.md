# Design: studio-students-calendar-enroll

## 1. Student email unification

Mirror instructors:

- API create/patch: `email` + optional `password` (password requires email).
- Response: `email` canonical (User.email when `user_id` set); `login_email` MAY remain as read-only alias of login for one release or be dropped from student response — prefer single `email` in UI; response can keep `login_email` = same as email when linked for compatibility.
- Create/update: if password provided → create/update User role `alumno` with that email; profile `email` stays in sync with login when linked.
- Edit PATCH: omit `email` when unchanged; password only when explicitly set.
- Data: one-time align `studio_students.email` ← User.email where linked (Alembic or startup script in migration).

## 2. Alumnos UI

- Create form fields: full_name (required), email (optional empty), password (optional empty), document/emergency/medical as today, active.
- No browser autofill: `autoComplete="off"` / `new-password`.
- List rows: name + summary; actions **Editar** | **Eliminar** (soft `active=false`).
- Edit modal: same fields + optional new password; errors inside modal.

## 3. Calendar enroll (puntual)

### Preconditions
- Slot has `series_id` + instructor (already assigned).
- Remaining capacity = `series.capacity` (or session.capacity) − count of active bookings for that session/date.
- Student active; not already booked on that session.

### Flow
```
POST /api/v1/studio/calendar/enroll
  { series_id, session_date, student_id }
→ ensure ClassSession(series_id, session_date) exists (create from series if missing; holiday → still allow or reject? Prefer reject enroll on holiday with 422)
→ capacity check
→ Booking(student, session, pack_id=NULL, status=booked)
→ no credit mutation
```

Admin JWT; **not** behind `require_schedule_active`.

### Capacity display
Availability (or enroll preview) SHOULD expose `booked_count` / `remaining_capacity` on assigned slots so UI can hide enroll when full.

## 4. Schema

- Alembic: `studio_bookings.pack_id` **nullable**; classic book paths still require pack.
- Optional: same for any related constraints.

## 5. Frontend calendar modal

When slot assigned:
- Show instructor (existing)
- Section **Alumnos**: select student + list already enrolled that day; button Asignar if `remaining > 0`
- If no series_id: keep instructor-only assign (no student enroll)

## 6. Out of scope (design)

Packs, waitlist, alumno portal, fixed enrollment from calendar.
