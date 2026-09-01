# Delta: Studio Scheduling — instructors edit UI + activity catalog

## MODIFIED Requirements

### Requirement: Instructors

Admin MUST CRUD studio instructors with: `full_name`, optional contact `email`, optional `phone`, optional login (`login_email` + `password` together), `active` flag, and **zero or more activity associations** (`activity_ids`). Create and update MUST accept `activity_ids` as a list (empty allowed). Response MUST include `activity_ids`. Activity links are **catalog only** and MUST NOT filter the Series instructor picker or block writes based on existing series/sessions.

On Estudio → Instructores, admin MUST create with activity checkboxes (active activities). Each row MUST expose **Editar** (modal: name, email, phone, activities, active, optional login credentials; validation errors **inside** the modal) and **Eliminar** (soft: `active=false`; row remains listed as inactive). Hard-delete MUST NOT be used. Inactive instructors MUST remain visible on the list and MAY be reactivated via Editar.

Instructors MUST remain assignable to series/sessions regardless of `activity_ids`. An instructor user MUST see only their agenda (`GET /studio/instructor/sessions`). Write access MUST remain AdminOnly.

(Previously: instructors had API CRUD but UI was create-only with a plain list; no activity association.)

#### Scenario: Create instructor with two activities
- **GIVEN** an admin and two active activities
- **WHEN** they create an instructor with those `activity_ids`
- **THEN** GET instructors MUST return the instructor with both activity ids

#### Scenario: Create with no activities allowed
- **GIVEN** an admin
- **WHEN** they create an instructor with empty `activity_ids`
- **THEN** the instructor MUST be created with an empty association set

#### Scenario: Edit updates profile, activities, and login
- **GIVEN** an existing instructor
- **WHEN** admin opens Editar, changes name, activity set, `active`, and supplies a new `login_email` + `password` pair
- **THEN** list and GET MUST reflect the new values
- **AND** validation errors MUST appear inside the modal

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

## Out of scope (this change)
- Teachers (`/teachers`) integration
- Staff write access
- Series validation against instructor activities
- Hard-delete of instructors
