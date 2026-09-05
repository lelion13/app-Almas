# Delta: Studio Students — email unify + calendar enroll

## ADDED Requirements

### Requirement: Calendar one-off student enroll (admin)

While viewing Estudio Calendario, admin MUST be able to assign an active student to a slot that already has an instructor (`series_id` present) for **that calendar date only**, when remaining capacity is greater than zero.

Capacity MUST be `session_or_series.capacity − count(active bookings for that session)`. Pack/credit MUST NOT be required for this path. The enroll API MUST remain available while `STUDIO_SCHEDULE_PAUSED` is true.

If no `ClassSession` exists for `(series_id, date)`, the system MUST create one from the series (unless the date is a holiday for that site/global — then enroll MUST fail with `422`). Duplicate booking for the same student/session MUST fail with `422`.

#### Scenario: Enroll when capacity free
- **GIVEN** a series slot capacity 2 with 1 active booking on date D
- **WHEN** admin enrolls another student for D
- **THEN** a booking MUST be created without pack
- **AND** remaining capacity MUST become 0

#### Scenario: Reject when full
- **GIVEN** remaining capacity 0
- **WHEN** admin attempts enroll
- **THEN** the response MUST be `422`

#### Scenario: Enroll under pause
- **GIVEN** `STUDIO_SCHEDULE_PAUSED` is true
- **WHEN** admin calls `POST /api/v1/studio/calendar/enroll`
- **THEN** the response MUST NOT be `410` solely due to the pause gate

## MODIFIED Requirements

### Requirement: Student profiles

Admin MUST CRUD students with personal data and optional document/emergency/medical fields.

**Email:** UI and write APIs MUST use a **single `email` field** (contact and login). Creating/updating login MUST use `email` + optional `password` together when enabling access (password requires email). When a User is linked, response `email` MUST be the canonical login email. Profile-only edits MUST allow omitting `email` when unchanged. Attempting to use an email owned by another User MUST return `409`/`422` with a clear message.

`StudentResponse` MUST NOT inherit instructor-only fields (`activity_ids`).

On Estudio → Alumnos, create form MUST show email and password as **empty optional** fields (not prefilled). Each row MUST expose **Editar** (modal; validation errors inside) and **Eliminar** (soft `active=false`) on the right, consistent with Instructores.

#### Scenario: Create without access
- **GIVEN** admin creates a student with name only (no email/password)
- **WHEN** saved
- **THEN** the student MUST exist with no `user_id`

#### Scenario: Create with access
- **GIVEN** admin creates a student with email + password (≥8)
- **WHEN** saved
- **THEN** a User role `alumno` MUST exist with that email
- **AND** student `email` MUST match

#### Scenario: Edit and soft delete
- **GIVEN** an existing student
- **WHEN** admin uses Editar / Eliminar
- **THEN** updates MUST persist via modal
- **AND** Eliminar MUST set `active=false` while keeping the row listed as inactive
