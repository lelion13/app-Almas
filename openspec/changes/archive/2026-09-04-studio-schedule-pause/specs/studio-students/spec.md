# Delta: Studio Students — pause booking portals

## ADDED Requirements

### Requirement: Booking and waitlist pause

While `STUDIO_SCHEDULE_PAUSED` is enabled, fixed-enrollment, booking cancel (admin), waitlist, attendance, and alumno portal booking APIs (`/me/packs`, `/me/sessions`, `/me/book`, `/me/bookings`, `/me/waitlist`, cancel, waitlist confirm) MUST respond with **410 Gone**.

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
