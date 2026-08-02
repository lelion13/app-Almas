# Delta: Auth — studio roles

## ADDED Requirements

### Requirement: Studio roles

The system MUST support user roles: `admin`, `staff` (existing), `instructor`, and `alumno`.

- `admin` MUST access studio administration (sedes, rooms, activities, students, packs, config, audit, mass cancel) and existing Almas admin features.
- `instructor` MUST access only their own agenda and attendance for sessions they instruct; MUST NOT access other instructors’ financial/admin data or pack payment management.
- `alumno` MUST access only their own portal (credits, upcoming bookings, book/cancel/waitlist confirm for self).
- `staff` MUST retain existing closing/expense behavior; studio admin capabilities for `staff` MAY be denied unless later granted (MVP: studio write/admin is `admin` only; `staff` MAY be read-only or excluded from studio — default **excluded from studio admin**).

#### Scenario: Instructor cannot manage packs
- **GIVEN** an authenticated instructor
- **WHEN** they call pack payment or student credit mutation APIs
- **THEN** the response MUST be `403`

#### Scenario: Alumno cannot see other students
- **GIVEN** an authenticated alumno
- **WHEN** they request another student’s profile or bookings
- **THEN** the response MUST be `403`

### Requirement: Admin creates login with temporary password

Admin MUST be able to create a User linked to an Instructor or Student profile with a temporary password (bcrypt-hashed). The system MUST NOT log or return the password after the create response (create response MAY include the temporary password **once** to the admin UI only, or require admin to set it in the same request — design chooses; MUST NOT persist plaintext).

#### Scenario: Create alumno user
- **GIVEN** an admin creating a student with login
- **WHEN** the create succeeds
- **THEN** a User with role `alumno` MUST exist linked to that student and password MUST be stored as bcrypt hash only
