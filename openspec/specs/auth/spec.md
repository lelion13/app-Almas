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

Users MUST have a role of `admin` or `staff`. The JWT MUST carry the role claim. Backend dependencies MUST enforce:
- **StaffOrAdmin**: `admin` or `staff` for operational endpoints
- **AdminOnly**: `admin` for privileged mutations (teachers write, reopen finalized closing)

#### Scenario: Staff forbidden from admin-only route
- **Given** a valid JWT with role `staff`
- **When** an AdminOnly endpoint is called
- **Then** the response MUST be `403`

### Requirement: Frontend session

The frontend MUST store the access token in `localStorage` (key `almas_token`), attach it on authenticated `apiFetch` calls, and guard app routes so unauthenticated users are redirected to `/login`. Logout MAY be client-side only (discard token); `POST /api/v1/auth/logout` MAY return `204` without server-side session revocation.

### Requirement: Security defaults

The system MUST NOT log passwords, JWTs, or password hashes. Production (`APP_ENV=production`) MUST disable OpenAPI docs (`/docs`, `/redoc`, `/openapi.json`). There is no refresh-token flow in scope.

### Requirement: User provisioning (ops)

Creating users MUST be available via operational tooling (`backend/scripts/create_user.py`). The product API MUST NOT expose public user registration. Password recovery UI is OUT OF SCOPE; ops MAY reset passwords via controlled scripts when available.

## Out of scope
- OAuth / social login
- Refresh tokens
- Self-service password reset email flow
