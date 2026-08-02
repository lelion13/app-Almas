# Delta: Studio Scheduling

## ADDED Requirements

### Requirement: Activities

Admin MUST define activities (e.g. Pilates, Yoga, Postural) with: name, level (`inicial`|`intermedio`|`avanzado`), default duration, and linkage to allowed rooms/instructors as designed.

### Requirement: Recurring sessions and instances

Admin MUST define recurring class templates (e.g. every Monday 18:00) with: room, activity, instructor, max student capacity (≤ room capacity), duration, level.

The system MUST materialize or resolve **session instances** for a date range for booking/attendance. Two sessions MUST NOT overlap in the same room.

#### Scenario: Room overlap rejected
- **GIVEN** an existing session in room R at time T
- **WHEN** admin creates another overlapping session in room R
- **THEN** the system MUST reject with validation error

### Requirement: Holidays and exceptions

Admin MUST manage holidays / non-working days and per-occurrence exceptions (cancel or override a single recurrence). Affected instances MUST not accept new bookings when cancelled.

#### Scenario: Holiday cancels occurrence
- **GIVEN** a recurring Monday class and a holiday on that Monday
- **WHEN** instances are resolved
- **THEN** that occurrence MUST be marked cancelled/unavailable

### Requirement: Instructors

Admin MUST CRUD instructors (profile + optional User login). Instructors MUST be assignable to sessions. An instructor user MUST see only their agenda.

### Requirement: Mass cancel session

Admin (or assigned instructor, if permitted by design — MVP: **admin** and **assigned instructor**) MUST cancel an entire session instance, releasing or handling bookings per credit rules (return credits to affected students) and recording audit. Students MUST see the cancellation in-app (no email required).

#### Scenario: Mass cancel returns credits
- **GIVEN** a session with booked students
- **WHEN** it is mass-cancelled
- **THEN** each active booking MUST be cancelled and credits returned per pack rules
- **AND** an audit entry MUST be written
