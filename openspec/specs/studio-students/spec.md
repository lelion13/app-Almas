# Studio Students & Bookings

## Purpose
Student profiles, fixed and mobile booking, waitlist confirm, attendance, and credit effects.

## Requirements

### Requirement: Booking and waitlist pause

While `STUDIO_SCHEDULE_PAUSED` is enabled, fixed-enrollment, booking cancel (admin), waitlist, attendance, and alumno portal booking APIs (`/me/packs`, `/me/sessions`, `/me/book`, `/me/bookings`, cancel, waitlist confirm) MUST respond with **410 Gone**.

Student profile CRUD (admin Estudio → Alumnos) MUST remain available.

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

Admin MUST CRUD students with personal data, optional contact/document/emergency/medical fields. A student MAY be linked to a User with role `alumno` when `login_email` + `password` are provided together at create. `StudentResponse` MUST NOT inherit instructor-only fields (e.g. `activity_ids`); student list endpoints MUST serialize via a dedicated student response builder.

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
