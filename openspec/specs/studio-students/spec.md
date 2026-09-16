# Studio Students & Bookings

## Purpose
Student profiles, fixed and mobile booking, waitlist confirm, attendance, and credit effects.

## Requirements

### Requirement: Booking and waitlist pause

While `STUDIO_SCHEDULE_PAUSED` is enabled, fixed-enrollment, booking cancel (admin), waitlist, attendance, and alumno portal booking APIs (`/me/packs`, `/me/sessions`, `/me/book`, `/me/bookings`, cancel, waitlist confirm) MUST respond with **410 Gone**.

Student profile CRUD (admin Estudio → Alumnos) MUST remain available.

**Carve-out:** `POST /api/v1/studio/calendar/enroll` MUST remain available (admin one-off enroll without pack). See `studio-scheduling`.

Alumno UI (`/mis-clases` and RoleIndex for `alumno`) MUST show a reconstruction stub and MUST NOT call paused `/me/*` booking APIs.

#### Scenario: Alumno portal stub
- **GIVEN** an authenticated alumno and pause enabled
- **WHEN** they open Mis clases
- **THEN** they MUST see a reconstruction message
- **AND** the page MUST NOT call `/me/book` or related paused endpoints

#### Scenario: Student catalog still works
- **GIVEN** pause enabled
- **WHEN** admin creates or lists students
- **THEN** the response MUST be `200`

### Requirement: Student profiles

Admin MUST CRUD students with personal data and optional document/emergency/medical fields.

**Email (unified):** UI and write APIs MUST use a **single `email` field** (contact and login), matching instructors. Creating or updating login MUST use `email` + optional `password` (password requires email; min length 8). When a User is linked, response `email` MUST be the canonical login email; `login_email` in the response MAY equal that same value when linked (compatibility) and MUST be null when there is no login.

Profile-only edits MUST allow omitting `email` when unchanged (PATCH omit). Explicit email change MUST sync `User.email`. Attempting to use an email owned by another User MUST return `409`/`422` with a clear Spanish message.

`StudentResponse` MUST NOT inherit instructor-only fields (`activity_ids`). Student list endpoints MUST serialize via a dedicated student response builder.

On Estudio → Alumnos:
- Create form MUST show email and password as **empty optional** fields (not prefilled; autofill discouraged via `autoComplete`).
- Each row MUST expose **Editar** (modal; validation errors inside) and **Eliminar** (soft `active=false`) on the right, consistent with Instructores.
- Inactive students MUST remain listed and MAY be reactivated via Editar.

Migration **`015`** MUST align `studio_students.email` to linked `users.email` where `user_id` is set and values diverge.

#### Scenario: Create without access
- **GIVEN** admin creates a student with name only (no email/password)
- **WHEN** saved
- **THEN** the student MUST exist with no `user_id`

#### Scenario: Create with access
- **GIVEN** admin creates a student with email + password (≥8)
- **WHEN** saved
- **THEN** a User role `alumno` MUST exist with that email
- **AND** student `email` MUST match

#### Scenario: Edit profile without changing email
- **GIVEN** a student with linked login
- **WHEN** admin saves Editar omitting `email`
- **THEN** the save MUST succeed
- **AND** `User.email` MUST remain unchanged

#### Scenario: Edit and soft delete
- **GIVEN** an existing active student
- **WHEN** admin clicks Eliminar
- **THEN** the student MUST have `active=false`
- **AND** it MUST still appear on the Alumnos list as inactive

### Requirement: Calendar one-off student enroll (admin)

While viewing Estudio Calendario, admin MUST be able to assign an active student to a slot that already has an instructor (`series_id` present) for **that calendar date only**, when remaining capacity is greater than zero.

Capacity MUST be `session.capacity − count(active bookings for that session)` (session capacity comes from the series when the session is created). Pack/credit MUST NOT be required. Booking `source` MUST be `calendar` and `pack_id` MUST be null.

If no `ClassSession` exists for `(series_id, date)`, the system MUST create one from the series. If the date is a holiday (global or site-scoped for the series site), enroll MUST fail with `422`. If the session is cancelled, enroll MUST fail with `422`. Duplicate active booking for the same student/session MUST fail with `422`. Full capacity MUST fail with `422`.

The enroll API `POST /api/v1/studio/calendar/enroll` MUST remain available while `STUDIO_SCHEDULE_PAUSED` is true.

Cancel of a calendar booking (when cancel APIs are unpaused) MUST NOT attempt to restore credits when `pack_id` is null.

#### Scenario: Enroll when capacity free
- **GIVEN** a series slot capacity 2 with 1 active booking on date D
- **WHEN** admin enrolls another student for D
- **THEN** a booking MUST be created with `pack_id` null and `source=calendar`
- **AND** remaining capacity MUST become 0

#### Scenario: Reject when full
- **GIVEN** remaining capacity 0
- **WHEN** admin attempts enroll
- **THEN** the response MUST be `422`

#### Scenario: Reject on holiday
- **GIVEN** date D is a holiday for the series site (or global)
- **WHEN** admin attempts enroll for D
- **THEN** the response MUST be `422`

#### Scenario: Enroll under pause
- **GIVEN** `STUDIO_SCHEDULE_PAUSED` is true
- **WHEN** admin calls `POST /api/v1/studio/calendar/enroll`
- **THEN** the response MUST NOT be `410` solely due to the pause gate

### Requirement: Fixed and mobile enrollment

- **Fixed:** admin creates `fixed-enrollments` (student + series + pack); system books future scheduled sessions for that series when credits/capacity allow.
- **Mobile:** alumno books individual sessions (`POST /me/book`) with `session_id` + `pack_id`, seeing scheduled sessions (`GET /me/sessions`).

Booking MUST require an active pack with remaining credits, paid status, and valid sede scope for the session’s sede. Concurrent booking MUST lock session/pack rows and reject when capacity is reached.

#### Scenario: Full class rejects booking
- **GIVEN** a session at capacity
- **WHEN** a mobile book is attempted
- **THEN** the system MUST reject booking (waitlist MAY be used separately)

### Requirement: Cancel booking and credit return

Alumno MUST cancel their own booking (`POST /me/bookings/{id}/cancel`) and recover one credit. Admin MUST cancel any booking. Credits MUST return on cancel of a booked (non-already-cancelled) booking.

#### Scenario: Alumno cancel returns credit
- **GIVEN** an alumno with a future booking consuming a credit
- **WHEN** they cancel
- **THEN** the booking MUST be cancelled and pack remaining credits MUST increase by one

### Requirement: Waitlist

When joining waitlist (`POST /me/waitlist`), the system MUST append ordered entries. The system MUST **not** auto-enroll when a spot frees. Alumno or admin confirms (`POST /me/waitlist/{id}/confirm` with `pack_id`), which creates a booking if capacity/pack allow and removes the waitlist entry. Alumno MUST be able to list own waitlist entries (`GET /me/waitlist`).

#### Scenario: Confirm from waitlist
- **GIVEN** a free spot and a waitlisted alumno with credits
- **WHEN** alumno or admin confirms with a valid pack
- **THEN** a booking MUST be created and waitlist entry removed

### Requirement: Attendance and lost-class policy

Instructor (own sessions) MUST set attendance: `presente` | `ausente` | `tarde` (`POST /instructor/attendance`). Admin MAY use settings (`no_show_deducts_credit`) for policy knobs.

**Shipped credit model:** a booking **consumes one credit at book time**. Cancel returns the credit. Therefore `ausente` MUST NOT deduct a second credit; the consumed credit is retained by non-cancel (lost-class is the consumption itself). Settings flags remain available for future policy tuning.

#### Scenario: Mark ausente
- **GIVEN** a session booking
- **WHEN** instructor marks `ausente`
- **THEN** attendance MUST persist and an audit entry MAY be written
- **AND** the system MUST NOT double-deduct credits beyond the original book consumption

## Out of scope
- Pre-class check-in kiosk
- Timed reschedule windows
- Plan freeze
- Auto-notify waitlist when spot opens
