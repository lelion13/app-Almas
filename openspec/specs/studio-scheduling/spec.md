# Studio Scheduling

## Purpose
Activities, recurring series, session materialization, holidays, instructors’ schedule assignment, and mass cancellation.

## Requirements

### Requirement: Activities

Admin MUST define activities (name, level string e.g. `inicial`/`intermedio`/`avanzado`, default duration minutes, active flag).

### Requirement: Recurring series and sessions

Admin MUST define recurring class series with: site, room, activity, instructor, weekday (`0`–`6`), start time, duration, capacity (≤ room capacity), level.

The system MUST expand series into **session instances** over a configurable week horizon (`POST /expand-sessions?weeks_ahead=`). Two **active** series MUST NOT overlap in the same room on the same weekday/time range (half-open intervals).

#### Scenario: Room overlap rejected
- **GIVEN** an existing active series in room R at a time that overlaps
- **WHEN** admin creates another overlapping series in room R same weekday
- **THEN** the system MUST reject with a validation error

### Requirement: Holidays and exceptions

Admin MUST manage holidays (`holiday_date`, name, optional `site_id`). Expansion MUST skip occurrences that match a holiday (site-scoped or global). Cancelled sessions MUST not accept new bookings.

### Requirement: Instructors

Admin MUST CRUD instructors (profile + optional User login with role `instructor`). Instructors MUST be assignable to series/sessions. An instructor user MUST see only their agenda (`GET /studio/instructor/sessions`).

### Requirement: Mass cancel session

Admin MUST cancel an entire session instance (`POST /sessions/{id}/mass-cancel`), setting session status to cancelled, cancelling active bookings, returning credits to packs, and writing audit. Students MUST learn of cancellation via in-app booking status (no email).

#### Scenario: Mass cancel returns credits
- **GIVEN** a session with booked students
- **WHEN** it is mass-cancelled
- **THEN** each active booking MUST be cancelled and credits returned
- **AND** an audit entry MUST be written

## Shipped notes
- Overlap uses half-open minute ranges (`times_overlap`).
- Mass cancel is **admin API** in MVP (not instructor HTTP route).
- Session expand respects holidays by date and optional site key.

## Out of scope
- Timed reschedule / move-with-caps
- Google Calendar sync
- Automatic notifications
