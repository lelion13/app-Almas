# Auth

## Purpose
Authenticate users with email/password, issue short-lived JWTs, and enforce role-based access on protected API and UI routes.

## Requirements

### Requirement: Login issues JWT on valid credentials

The system MUST authenticate users by email (case-insensitive, trimmed) and password verified with bcrypt. On success the system MUST return a Bearer access token (JWT HS256) containing claims `sub` (user id) and `role`. On failure the system MUST respond with a generic invalid-credentials message that does not reveal whether the email exists.

#### Scenario: Successful login
- **Given** a user exists with a valid bcrypt password hash
- **When** `POST /api/v1/auth/login` is called with correct email and password
- **Then** the response MUST be `200` with `access_token` and `token_type` `"bearer"`

#### Scenario: Failed login is generic
- **Given** wrong password or unknown email
- **When** login is attempted
- **Then** the response MUST be an auth failure with a generic message (no user enumeration)

### Requirement: Current user endpoint

The system MUST expose `GET /api/v1/auth/me` requiring a valid JWT. The response MUST include identity fields needed by the UI (at least id, email, role) and MUST NOT include password hashes.

#### Scenario: Valid token
- **Given** a non-expired JWT for an existing user
- **When** `GET /api/v1/auth/me` is called with `Authorization: Bearer <token>`
- **Then** the response MUST be `200` with the user profile

#### Scenario: Missing or invalid token
- **Given** no token or an invalid/expired token
- **When** a protected endpoint is called
- **Then** the response MUST be `401`

### Requirement: Roles

Users MUST have a role of `admin`, `staff`, `instructor`, or `alumno`. The JWT MUST carry the role claim. Backend dependencies MUST enforce at least:
- **StaffOrAdmin**: `admin` or `staff` for operational closing/expense endpoints
- **AdminOnly**: `admin` for privileged mutations (teachers write, reopen finalized closing, studio admin)
- **InstructorOnly**: `instructor` for instructor agenda/attendance
- **AlumnoOnly**: `alumno` for student portal (`/studio/me/*`)

#### Scenario: Staff forbidden from admin-only route
- **Given** a valid JWT with role `staff`
- **When** an AdminOnly endpoint is called
- **Then** the response MUST be `403`

### Requirement: Studio roles

The system MUST support studio-scoped portal access via role:

- `admin` MUST access studio administration (sedes, rooms, activities, students, packs, config, audit, mass cancel) and existing Almas admin features.
- `instructor` MUST access only their own agenda and attendance for sessions they instruct; MUST NOT manage pack payments or other students.
- `alumno` MUST access only their own portal (credits, bookings, book/cancel/waitlist confirm for self).
- `staff` MUST retain existing closing/expense behavior; studio admin write APIs MUST be `admin` only (staff excluded from studio admin in MVP).

#### Scenario: Instructor cannot manage packs
- **GIVEN** an authenticated instructor
- **WHEN** they call pack payment or student credit mutation APIs
- **THEN** the response MUST be `403`

#### Scenario: Alumno cannot see other students
- **GIVEN** an authenticated alumno
- **WHEN** they request another student’s profile or bookings
- **THEN** the response MUST be `403`

### Requirement: Admin creates login with temporary password

Admin MUST be able to create a User linked to an Instructor or Student profile with a password supplied in the same create request (bcrypt-hashed). `login_email` and `password` MUST be supplied together (both or neither). The system MUST NOT log or return the password after create (admin sets it once in the form). Password recovery UI remains OUT OF SCOPE.

#### Scenario: Create alumno user
- **GIVEN** an admin creating a student with login
- **WHEN** the create succeeds
- **THEN** a User with role `alumno` MUST exist linked to that student and password MUST be stored as bcrypt hash only

### Requirement: Frontend session

The frontend MUST store the access token in `localStorage` (key `almas_token`), attach it on authenticated `apiFetch` calls, and guard app routes so unauthenticated users are redirected to `/login`. Role MUST drive landing and nav:
- `alumno` → Mis clases (`/mis-clases`)
- `instructor` → Mi agenda (`/instructor`)
- `admin` / `staff` → Cierres (and admin-only Estudio/Conciliación/Profesoras as applicable)

Logout MAY be client-side only (discard token); `POST /api/v1/auth/logout` MAY return `204` without server-side session revocation.

### Requirement: Security defaults

The system MUST NOT log passwords, JWTs, or password hashes. Production (`APP_ENV=production`) MUST disable OpenAPI docs (`/docs`, `/redoc`, `/openapi.json`). There is no refresh-token flow in scope.

### Requirement: User provisioning (ops)

Creating users MUST be available via operational tooling (`backend/scripts/create_user.py`) and via studio admin create (instructor/alumno with login). The product API MUST NOT expose public user registration. Password recovery UI is OUT OF SCOPE; ops MAY reset passwords via controlled scripts when available.

## Out of scope
- OAuth / social login for Almas users
- Refresh tokens
- Self-service password reset email flow
- Role `recepción`
