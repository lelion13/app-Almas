# Delta: Studio Scheduling — calendar availability

## ADDED Requirements

### Requirement: Estudio calendar availability

Admin MUST have an Estudio **Calendario** week view (Mon–Sun) that shows availability slots computed from **room open hours**, **room capacity**, and each linked activity’s **default duration** (catalog tiling). Slot generation MUST NOT depend on materialized sessions.

Filters MUST cascade: selecting a site narrows rooms to that site; selecting an activity narrows rooms to those linked via `room_ids`. Filters MAY be empty (show all matching active catalog).

Weekday for hours and series MUST use **0=Sunday … 6=Saturday** (same as room-hours UI).

The calendar MUST remain available while `STUDIO_SCHEDULE_PAUSED` is true (dedicated APIs MUST NOT return 410 solely due to the pause gate).

Holidays in the week MUST still show the day column, marked as feriado (attenuated in UI). Slots MAY still appear.

Active class series MUST be overlaid onto matching slots (`room_id` + `activity_id` + `weekday` + `start_time`). Overlay fields MUST include `series_id`, `instructor_id`, and `instructor_name` when assigned.

#### Scenario: Tile slots by activity duration
- **GIVEN** room open 08:00–10:00 and activity duration 60 linked to that room
- **WHEN** admin loads the week containing that weekday
- **THEN** slots MUST include 08:00–09:00 and 09:00–10:00 for that activity/room
- **AND** each slot MUST expose the room capacity

#### Scenario: Cascade filters
- **GIVEN** site S with rooms R1, R2 and activity A linked only to R1
- **WHEN** admin selects site S and activity A
- **THEN** the room filter options MUST only include R1

#### Scenario: Usable under schedule pause
- **GIVEN** `STUDIO_SCHEDULE_PAUSED` is true
- **WHEN** admin calls `GET /api/v1/studio/calendar/availability`
- **THEN** the response MUST NOT be `410` solely due to the pause gate

#### Scenario: Assigned instructor visible on slot
- **GIVEN** an active series for room R, activity A, weekday W, start 09:00 with instructor I
- **WHEN** admin loads the calendar week
- **THEN** the matching slot MUST include `instructor_name` for I
- **AND** reopening the slot modal MUST preselect I

#### Scenario: Holiday day attenuated
- **GIVEN** a holiday on date D in the requested week
- **WHEN** admin views the calendar
- **THEN** day D MUST be visible and marked as feriado

### Requirement: Calendar slot instructor assignment

Admin MUST open a modal when clicking an availability slot. The modal MUST allow selecting an instructor from active instructors whose `activity_ids` include the slot’s activity. Confirming MUST create or update a class series via `POST /api/v1/studio/calendar/schedule`, which MUST remain available while schedule pause is enabled.

If a matching active series already exists (same room, activity, weekday, start_time), the endpoint MUST update the instructor instead of creating a duplicate. If the instructor is not linked to the activity, the API MUST return `422`.

#### Scenario: Filter instructors by activity
- **GIVEN** slot for activity Yoga
- **AND** instructor A linked to Yoga and instructor B linked only to Pilates
- **WHEN** admin opens the slot modal
- **THEN** the instructor list MUST include A and MUST NOT include B

#### Scenario: Schedule from calendar under pause
- **GIVEN** `STUDIO_SCHEDULE_PAUSED` is true
- **WHEN** admin confirms a slot with a valid instructor
- **THEN** `POST /api/v1/studio/calendar/schedule` MUST succeed (not `410`)
- **AND** a class series MUST be created or updated

#### Scenario: Reassign instructor on same slot
- **GIVEN** an existing series on a calendar slot
- **WHEN** admin selects a different valid instructor and confirms
- **THEN** the same series MUST be updated
- **AND** a second series for that slot MUST NOT be created

## MODIFIED Requirements

### Requirement: Schedule stack pause

Carve-out: calendar availability + schedule endpoints MUST NOT return 410 solely due to pause (see main spec after merge).
