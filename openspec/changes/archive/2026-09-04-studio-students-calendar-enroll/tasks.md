# Tasks: studio-students-calendar-enroll

## Phase 1: Backend students
- [x] 1.1 Align StudentCreate/Patch/Response to single `email` + optional password (instructor-like)
- [x] 1.2 Update `create_student` / `update_student` + response builder; tests for create with/without access
- [x] 1.3 Alembic: align linked student emails; `bookings.pack_id` nullable (**015**)

## Phase 2: Backend calendar enroll
- [x] 2.1 Expose `booked_count` / remaining / enrolled on assigned calendar slots
- [x] 2.2 `ensure_session_for_series_date` + `enroll_student_on_calendar` (no pack, capacity check)
- [x] 2.3 `POST /studio/calendar/enroll` (AdminOnly, not paused) + schema tests

## Phase 3: Frontend Alumnos
- [x] 3.1 Replace ProfileSection students with Instructores-like create + Editar/Eliminar
- [x] 3.2 Single Email field; empty optional password; no autofill junk

## Phase 4: Frontend Calendario
- [x] 4.1 Slot modal: enroll student when series assigned and remaining > 0
- [x] 4.2 Show enrolled list / capacity; reload after enroll

## Phase 5: Docs & verify
- [x] 5.1 Update `studio-ops-lessons.md` + `runbook.md`
- [x] 5.2 pytest + `npm run build`
