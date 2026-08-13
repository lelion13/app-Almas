# Delta: Studio Scheduling — activity rooms + edit UI

## MODIFIED Requirements

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

(Previously: activity and room were independent.)

The system MUST expand series into **session instances** over a configurable week horizon (`POST /expand-sessions?weeks_ahead=`). Two **active** series MUST NOT overlap in the same room on the same weekday/time range (half-open intervals), **nor** in a room linked by `shares_space_with_room_id`. Unlinked rooms in the same site MAY overlap.

Class series create/update MUST be validated against the assigned room’s weekly open hours (see `studio-sites`). No open ranges on the weekday, or class interval not fully contained in **at least one** open range, MUST fail with `422` and a non-secret error detail suitable for UI display.

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

## Out of scope (this change)
- Hard-delete of activities
- Auto-backfill of rooms onto existing activities
- Prefill series duration from activity
- Packs scoped by activity
