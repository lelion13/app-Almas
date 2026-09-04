# Delta: Studio Scheduling — pause series/sessions ops

## ADDED Requirements

### Requirement: Schedule stack pause

While `STUDIO_SCHEDULE_PAUSED` is enabled, the system MUST NOT expose operational schedule APIs for series, session expand, session list, or mass-cancel. Those endpoints MUST respond with **410 Gone** and a clear Spanish detail that agenda/paquetes are under reconstruction.

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

## MODIFIED Requirements

### Requirement: Recurring series and sessions

While pause is enabled, the requirements for creating series, expanding sessions, and mass-cancel MUST be treated as **suspended** (not deleted). Data MAY remain in the database. Operators MUST NOT use admin UI for these flows.

### Requirement: Instructors

Instructor catalog CRUD and login MUST remain available. Instructor agenda APIs (`/instructor/sessions`, bookings, attendance) MUST return `410` while pause is enabled. Instructor UI MUST show a reconstruction stub instead of calling those APIs.

#### Scenario: Instructor portal stub
- **GIVEN** an authenticated instructor and pause enabled
- **WHEN** they open Mi agenda
- **THEN** they MUST see a reconstruction message
- **AND** the page MUST NOT call paused session APIs
