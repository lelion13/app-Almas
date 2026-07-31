# Teachers

## Purpose
Maintain the teacher catalog used by `teacher_hours` manual expenses.

## Requirements

### Requirement: Teacher entity

A teacher MUST have at least `full_name` and `active` (boolean). Soft-deactivation via `active=false` SHOULD be preferred over hard delete.

### Requirement: Read access

`GET /api/v1/teachers` MUST be available to StaffOrAdmin. Query param `include_inactive` MAY include inactive teachers (default behavior SHOULD exclude inactive unless requested).

### Requirement: Write access admin-only

`POST /api/v1/teachers` and `PATCH /api/v1/teachers/{teacher_id}` MUST require AdminOnly.

#### Scenario: Staff cannot create teacher
- **Given** a JWT with role `staff`
- **When** `POST /api/v1/teachers` is called
- **Then** the response MUST be `403`

### Requirement: Frontend

- Route `/teachers` (`TeachersPage`) MUST be reachable to admin users in the UI navigation
- Non-admin users MUST be redirected/blocked from the teachers page
- UI MUST support listing (including inactive when loaded) and creating teachers
- Edit/deactivate UI MAY be deferred; PATCH API remains in scope for ops/future UI

## Related
- `manual-expenses`, `auth`
