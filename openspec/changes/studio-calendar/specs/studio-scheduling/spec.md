# Delta: Studio Scheduling — calendar availability

## ADDED Requirements

### Requirement: Estudio calendar availability (read-only)

Admin MUST have an Estudio **Calendario** week view that shows availability slots computed from **room open hours**, **room capacity**, and each linked activity’s **default duration** (catalog). The view MUST NOT depend on class series or materialized sessions.

Filters MUST cascade: selecting a site narrows rooms to that site; selecting an activity narrows rooms to those linked via `room_ids`. Filters MAY be empty (show all matching active catalog).

The calendar MUST remain available while `STUDIO_SCHEDULE_PAUSED` is true (dedicated read API MUST NOT return 410 solely due to the pause gate).

Holidays in the week MUST still show the day column, marked as feriado (attenuated in UI). Slots MAY still appear.

MVP MUST be read-only (no booking or series create from this view).

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

#### Scenario: Holiday day attenuated
- **GIVEN** a holiday on date D in the requested week
- **WHEN** admin views the calendar
- **THEN** day D MUST be visible and marked as feriado
