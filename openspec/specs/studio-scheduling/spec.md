# Studio Scheduling

## Purpose
Activities, recurring series, session materialization, holidays, instructors’ schedule assignment, and mass cancellation.

## Requirements

### Requirement: Schedule stack pause

While `STUDIO_SCHEDULE_PAUSED` is enabled, the system MUST NOT expose operational schedule APIs for series list/create/patch/delete, session expand, session list, or mass-cancel. Those endpoints MUST respond with **410 Gone** and a clear Spanish detail that agenda/paquetes are under reconstruction.

**Carve-out:** `GET /api/v1/studio/calendar/availability` and `POST /api/v1/studio/calendar/schedule` MUST remain available (not 410) so Estudio Calendario can show catalog availability and assign instructors (creates/updates `ClassSeries` rows).

Catalog endpoints (sites, rooms, hours, activities, instructors, students, holidays, audit) MUST remain available.

Estudio admin UI MUST NOT show tabs **Series** or **Sesiones**.

#### Scenario: Series API paused
- **GIVEN** `STUDIO_SCHEDULE_PAUSED` is true
- **WHEN** admin calls `GET /api/v1/studio/series` or `POST /api/v1/studio/series`
- **THEN** the response MUST be `410`

#### Scenario: Expand paused
- **GIVEN** pause enabled
- **WHEN** admin calls `POST /api/v1/studio/expand-sessions`
- **THEN** the response MUST be `410`

#### Scenario: Catalog still works
- **GIVEN** pause enabled
- **WHEN** admin lists sites, rooms, activities, instructors, or students
- **THEN** the response MUST be `200`

#### Scenario: Calendar carve-out under pause
- **GIVEN** pause enabled
- **WHEN** admin calls `GET /api/v1/studio/calendar/availability` or `POST /api/v1/studio/calendar/schedule`
- **THEN** the response MUST NOT be `410` solely due to the pause gate

### Requirement: Estudio calendar availability

Admin MUST have an Estudio **Calendario** week view (Mon–Sun) that shows availability slots computed from **room open hours**, **room capacity**, and each linked activity’s **default duration** (catalog tiling). Slot generation MUST NOT depend on materialized sessions.

Filters MUST cascade: selecting a site narrows rooms to that site; selecting an activity narrows rooms to those linked via `room_ids`. Filters MAY be empty (show all matching active catalog).

Weekday for hours and series MUST use **0=Sunday … 6=Saturday** (same as room-hours UI).

Holidays in the week MUST still show the day column, marked as feriado (attenuated in UI). Slots MAY still appear.

Active class series MUST be overlaid onto matching slots (`room_id` + `activity_id` + `weekday` + `start_time`). Overlay fields MUST include `series_id`, `instructor_id`, and `instructor_name` when assigned. Unassigned slots MUST be distinguishable in the UI.

#### Scenario: Tile slots by activity duration
- **GIVEN** room open 08:00–10:00 and activity duration 60 linked to that room
- **WHEN** admin loads the week containing that weekday
- **THEN** slots MUST include 08:00–09:00 and 09:00–10:00 for that activity/room
- **AND** each slot MUST expose the room capacity

#### Scenario: Cascade filters
- **GIVEN** site S with rooms R1, R2 and activity A linked only to R1
- **WHEN** admin selects site S and activity A
- **THEN** the room filter options MUST only include R1

#### Scenario: Assigned instructor visible on slot
- **GIVEN** an active series for room R, activity A, weekday W, start 09:00 with instructor I
- **WHEN** admin loads the calendar week
- **THEN** the matching slot MUST include `instructor_name` for I
- **AND** reopening the slot modal MUST preselect I

#### Scenario: Holiday day attenuated
- **GIVEN** a holiday on date D in the requested week
- **WHEN** admin views the calendar
- **THEN** day D MUST be visible and marked as feriado

### Requirement: Calendar slot instructor assignment

Admin MUST open a modal when clicking an availability slot. The modal MUST allow selecting an instructor from active instructors whose `activity_ids` include the slot’s activity. Confirming MUST create or update a class series for that site/room/activity/weekday/start/duration/capacity via `POST /api/v1/studio/calendar/schedule`.

If a matching active series already exists (same room, activity, weekday, start_time), the endpoint MUST **update** the instructor (and related slot fields) instead of creating a duplicate. If the instructor is not linked to the activity, the API MUST return `422`.

#### Scenario: Filter instructors by activity
- **GIVEN** slot for activity Yoga
- **AND** instructor A linked to Yoga and instructor B linked only to Pilates
- **WHEN** admin opens the slot modal
- **THEN** the instructor list MUST include A and MUST NOT include B

#### Scenario: Schedule from calendar under pause
- **GIVEN** `STUDIO_SCHEDULE_PAUSED` is true
- **WHEN** admin confirms a slot with a valid instructor
- **THEN** `POST /api/v1/studio/calendar/schedule` MUST succeed (not `410`)
- **AND** a class series MUST be created or updated

#### Scenario: Reassign instructor on same slot
- **GIVEN** an existing series on a calendar slot
- **WHEN** admin selects a different valid instructor and confirms
- **THEN** the same series MUST be updated
- **AND** a second series for that slot MUST NOT be created

### Requirement: Activities

Admin MUST define activities with: name, level string (e.g. `inicial`/`intermedio`/`avanzado`), default duration minutes, active flag, and **one or more room associations** (`room_ids`). Create and update MUST reject payloads with zero rooms. Response MUST include `room_ids`. Rooms MAY belong to different sites. Existing activities with no rooms after migration MUST remain listable; new series using them MUST fail until rooms are assigned via edit.

On Estudio → Actividades, admin MUST create with room checkboxes (active rooms grouped by site). Each row MUST expose **Editar** (modal: name, level, duration, rooms, active; validation errors **inside** the modal) and **Eliminar** (soft: `active=false`; row remains listed as inactive). Hard-delete MUST NOT be used.

Inactive activities MUST remain visible on the Actividades admin list and MUST NOT appear in the Series activity picker.

#### Scenario: Create activity with two rooms
- **GIVEN** an admin and two active rooms (possibly different sites)
- **WHEN** they create an activity with those `room_ids`
- **THEN** GET activities MUST return the activity with both room ids

#### Scenario: Create without rooms rejected
- **GIVEN** an admin
- **WHEN** they POST an activity with empty `room_ids`
- **THEN** the response MUST be `422`

#### Scenario: Edit updates rooms and fields
- **GIVEN** an existing activity
- **WHEN** admin opens Editar, changes name and room set, and saves
- **THEN** list and GET MUST reflect the new values
- **AND** validation errors MUST appear inside the modal

#### Scenario: Soft delete
- **GIVEN** an existing active activity
- **WHEN** admin clicks Eliminar
- **THEN** the activity MUST have `active=false`
- **AND** it MUST still appear on the Actividades list as inactive
- **AND** it MUST NOT appear in the Series activity select

#### Scenario: Cannot unlink room used by active series
- **GIVEN** activity Yoga linked to rooms A and B
- **AND** an active series of Yoga in room A
- **WHEN** admin saves Editar with only room B
- **THEN** the response MUST be `422`

### Requirement: Recurring series and sessions

Admin MUST define recurring class series with: site, room, activity, instructor, weekday (`0`–`6`, domingo…sábado), start time, duration, capacity (≤ room capacity), level.

The chosen `room_id` MUST belong to the activity’s associated rooms. The Series admin room picker MUST offer only rooms that are in the selected site **and** linked to the selected activity.

The system MUST expand series into **session instances** over a configurable week horizon (`POST /expand-sessions?weeks_ahead=`). Two **active** series MUST NOT overlap in the same room on the same weekday/time range (half-open intervals), **nor** in a room linked by `shares_space_with_room_id`. Unlinked rooms in the same site MAY overlap.

Class series create/update MUST be validated against the assigned room’s weekly open hours (see `studio-sites`). No open ranges on the weekday, or class interval not fully contained in **at least one** open range, MUST fail with `422` and a non-secret error detail suitable for UI display.

While `STUDIO_SCHEDULE_PAUSED` is enabled, the requirements for creating series, expanding sessions, and mass-cancel MUST be treated as **suspended** (not deleted). Data MAY remain in the database. Operators MUST NOT use admin UI for these flows.

#### Scenario: Series room not linked to activity rejected
- **GIVEN** activity Yoga linked only to room A
- **WHEN** admin creates a series with Yoga and room B
- **THEN** the response MUST be `422`

#### Scenario: Series picker filters by activity and site
- **GIVEN** activity Yoga linked to rooms in sites X and Y
- **AND** admin selected site X and activity Yoga
- **WHEN** the Salón dropdown is shown
- **THEN** only Yoga’s rooms that belong to site X MUST appear

#### Scenario: Room overlap rejected
- **GIVEN** an existing active series in room R at a time that overlaps
- **WHEN** admin creates another overlapping series in room R same weekday
- **THEN** the system MUST reject with a validation error

#### Scenario: Shared-space series overlap rejected
- **GIVEN** Yoga shares space with Postural
- **AND** Yoga has an active Monday series 10:00 duration 60
- **WHEN** admin creates a Postural Monday series 10:30 duration 60
- **THEN** the system MUST reject with a validation error

#### Scenario: Overlap still checked after hours pass
- **GIVEN** a valid in-hours series slot that overlaps another series in the same room
- **WHEN** admin creates the second series
- **THEN** the system MUST still reject due to room time overlap

### Requirement: Holidays and exceptions

Admin MUST manage holidays (`holiday_date`, name, optional `site_id`). Expansion MUST skip occurrences that match a holiday (site-scoped or global). Cancelled sessions MUST not accept new bookings.

### Requirement: Instructors

Admin MUST CRUD studio instructors with: `full_name`, optional `email`, optional `phone`, optional login via `password` (requires `email` on create or when first enabling login), `active` flag, and **zero or more activity associations** (`activity_ids`). Create and update MUST accept `activity_ids` as a list (empty allowed). Response MUST include `activity_ids`, optional `user_id`, and read-only `login_email` (canonical linked User email when `user_id` is set; MUST match response `email` when linked).

**API contract (instructors vs students):** `InstructorCreate` / `InstructorPatch` MUST use **`email` + optional `password`** — MUST NOT use `login_email` (students/alumnos still use `login_email` + `password` pair). When an instructor has `user_id`, GET list/detail MUST return canonical `email` from the linked User.

**Email and login rules:**
- UI MUST expose a **single “Email” field** (no separate “email de acceso”).
- UI edit PATCH MUST **omit `email`** from the JSON body when the value is unchanged (case-insensitive compare).
- UI edit MUST send `password` only when the admin explicitly edited the password field (MUST NOT send browser-autofill password).
- Backend MUST update `User.email` **only** when `email` is present in PATCH and normalized value differs from the current login.
- Profile-only edits (name, phone, activities, active) MUST succeed without re-validating email ownership when `email` is omitted.
- Attempting to assign an email already owned by another User MUST return `422` with a clear message.

**Junction replace (M2M):** `replace_instructor_activities` (and analogous activity-room / room-hours replace helpers) MUST call `db.flush()` after row deletes and before inserts to avoid unique-constraint violations on `(instructor_id, activity_id)` that were previously misreported as email conflicts.

Activity links are **catalog only** and MUST NOT filter the Series instructor picker or block writes based on existing series/sessions.

On Estudio → Instructores, admin MUST create with activity checkboxes (active activities). Each row MUST expose **Editar** (modal: name, email, phone, activities, active, optional new password; validation errors **inside** the modal) and **Eliminar** (soft: `active=false`; row remains listed as inactive). Hard-delete MUST NOT be used. Inactive instructors MUST remain visible on the list and MAY be reactivated via Editar.

Instructors MUST remain assignable to series/sessions regardless of `activity_ids`. An instructor user MUST see only their agenda (`GET /studio/instructor/sessions`). Write access MUST remain AdminOnly.

Instructor catalog CRUD and login MUST remain available. Instructor agenda APIs (`/instructor/sessions`, bookings, attendance) MUST return `410` while pause is enabled. Instructor UI MUST show a reconstruction stub instead of calling those APIs.

Migration **`014_align_instructor_emails`** MUST align `studio_instructors.email` to linked `users.email` where `user_id` is set and values diverge (login email wins). Existing instructors after **`013`** keep zero activity links until an admin assigns them via Editar (no backfill).

#### Scenario: Create instructor with two activities
- **GIVEN** an admin and two active activities
- **WHEN** they create an instructor with those `activity_ids`
- **THEN** GET instructors MUST return the instructor with both activity ids

#### Scenario: Create with no activities allowed
- **GIVEN** an admin
- **WHEN** they create an instructor with empty `activity_ids`
- **THEN** the instructor MUST be created with an empty association set

#### Scenario: Create login from single email field
- **GIVEN** an admin
- **WHEN** they create an instructor with email `ana@studio.com` and password
- **THEN** the instructor MUST have `email` = `ana@studio.com`
- **AND** a User with role `instructor` MUST exist with email `ana@studio.com`
- **AND** the create payload MUST NOT require `login_email`

#### Scenario: Edit profile without changing email
- **GIVEN** an instructor with linked login `ire@studio.com`
- **WHEN** admin saves Editar changing only name or phone
- **AND** the PATCH body omits `email`
- **THEN** the save MUST succeed
- **AND** `User.email` MUST remain `ire@studio.com`

#### Scenario: Explicit email change syncs login
- **GIVEN** an instructor with `user_id` and login `old@studio.com`
- **WHEN** admin PATCH includes `email` = `new@studio.com`
- **THEN** the linked User email MUST become `new@studio.com`
- **AND** `422` MUST be returned if `new@studio.com` belongs to another User

#### Scenario: Edit updates activities on save
- **GIVEN** an instructor already linked to activity A
- **WHEN** admin saves Editar with the same `activity_ids` including A
- **THEN** the save MUST succeed (junction replace MUST NOT violate unique constraint)

#### Scenario: Soft delete and reactivate
- **GIVEN** an existing active instructor
- **WHEN** admin clicks Eliminar
- **THEN** the instructor MUST have `active=false`
- **AND** it MUST still appear on the Instructores list as inactive
- **WHEN** admin reopens Editar and sets `active=true`
- **THEN** the instructor MUST be active again

#### Scenario: Remove activity despite existing series
- **GIVEN** instructor I linked to activity A
- **AND** an active series for I teaching activity A
- **WHEN** admin saves Editar with `activity_ids` that omit A
- **THEN** the save MUST succeed
- **AND** existing series/sessions MUST remain unchanged

#### Scenario: Series picker not filtered by instructor activities
- **GIVEN** instructor I with no `activity_ids`
- **AND** activity Yoga selected in Series form
- **WHEN** the Instructor dropdown is shown
- **THEN** I MUST still appear as a selectable option

#### Scenario: Instructor portal stub
- **GIVEN** an authenticated instructor and pause enabled
- **WHEN** they open Mi agenda
- **THEN** they MUST see a reconstruction message
- **AND** the page MUST NOT call paused session APIs

## Shipped notes
- Overlap uses half-open minute ranges (`times_overlap`).
- Room open windows use half-open `[open_time, close_time)` (`open_time_ranges_overlap`).
- Mass cancel is **admin API** in MVP (not instructor HTTP route).
- Session expand respects holidays by date and optional site key.
- Hours API: `GET|PUT /api/v1/studio/rooms/{id}/hours` with `{ slots }`.
- `StudentResponse` MUST NOT inherit instructor-only fields (`activity_ids`); use separate profile response types.

### Requirement: Mass cancel session

Admin MUST cancel an entire session instance (`POST /sessions/{id}/mass-cancel`), setting session status to cancelled, cancelling active bookings, returning credits to packs, and writing audit. Students MUST learn of cancellation via in-app booking status (no email).

#### Scenario: Mass cancel returns credits
- **GIVEN** a session with booked students
- **WHEN** it is mass-cancelled
- **THEN** each active booking MUST be cancelled and credits returned
- **AND** an audit entry MUST be written

## Out of scope
- Timed reschedule / move-with-caps
- Google Calendar sync
- Automatic notifications
- Re-validating all historical series after hours edit
