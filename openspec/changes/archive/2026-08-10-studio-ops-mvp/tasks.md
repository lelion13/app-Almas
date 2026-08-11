# Tasks: studio-ops-mvp

## Phase 1: Foundation

- [x] 1.1 Extend `User.role` for `instructor` / `alumno`; auth deps + frontend route guards
- [x] 1.2 Alembic migration(s) for studio tables (sites, rooms, activities, instructors, students, series, sessions, holidays, packs, bookings, waitlist, attendance, audit, settings)
- [x] 1.3 Register `studio` API router prefix `/api/v1/studio`
- [x] 1.4 `StudioSettings` defaults (no_show_deducts_credit, etc.)

## Phase 2: Sites & schedule admin

- [x] 2.1 CRUD sedes + salones (admin API + UI)
- [x] 2.2 CRUD activities + instructors (profile + optional user+temp password)
- [x] 2.3 Class series CRUD + overlap validation + session materialization/expand
- [x] 2.4 Holidays / session exceptions
- [x] 2.5 Mass cancel session (credits return + audit + in-app status)

## Phase 3: Students, packs, credits

- [x] 3.1 CRUD students (+ optional user+temp password)
- [x] 3.2 Pack products + assign StudentPack (sede scope, payment method/status, trial)
- [x] 3.3 Gift/transfer credits between students + audit
- [x] 3.4 Admin student pack/payment history UI

## Phase 4: Bookings & waitlist

- [x] 4.1 Fixed enrollment assignment (admin)
- [x] 4.2 Mobile book with capacity lock + credit consume
- [x] 4.3 Cancel booking (alumno/admin/instructor) + credit return
- [x] 4.4 Waitlist join + confirm (no auto-enroll)
- [x] 4.5 Attendance + no-show policy application

## Phase 5: Portals

- [x] 5.1 Instructor agenda + attendance UI
- [x] 5.2 Alumno portal: packs remaining, upcoming, book, cancel, waitlist confirm
- [x] 5.3 Admin Estudio nav shell linking all admin screens

## Phase 6: Audit & quality

- [x] 6.1 Audit log writer on mutations + admin list UI
- [x] 6.2 Backend tests: roles 403, overlap, credits, waitlist confirm, mass cancel
- [x] 6.3 Update `docs/runbook.md` + `openspec` pointers; note coexistence with SigueFit

## Dependencies

- 1 before 2–5
- 2–3 before 4
- 4 before 5 (portal consumes booking APIs)
- 6 continuous / end
