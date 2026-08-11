# Delta: Studio Sites — rooms edit + weekly hours

## ADDED Requirements

### Requirement: Room default class duration

Each salón MUST store `default_class_duration_minutes` (integer ≥ 1). Create and update MUST accept this field. Existing rooms MUST receive a backfill (e.g. 60) when migrating. Series MAY use a different duration; the room value is the default for admin planning and MUST appear on create form and list.

#### Scenario: Create room with duration
- **GIVEN** an admin
- **WHEN** they create a room with site, name, capacity, and duration 45
- **THEN** the room MUST persist `default_class_duration_minutes = 45`

### Requirement: Room edit modal

On Estudio → Salones, each room MUST offer an **Editar** action that opens a modal to change: site (sede), name, capacity, default duration, and active flag, saved via PATCH.

#### Scenario: Edit capacity and duration
- **GIVEN** an existing room
- **WHEN** admin opens Editar, sets capacity and duration, and saves
- **THEN** list and subsequent GET MUST reflect new values

#### Scenario: Move site blocked if series exist
- **GIVEN** a room with at least one active class series
- **WHEN** admin attempts to change the room’s site_id
- **THEN** the system MUST reject with validation error

### Requirement: Room weekly open hours

Each salón MUST support a weekly schedule of **zero or more open time ranges per weekday** (0–6, domingo…sábado). Each range MUST have open_time and close_time with close_time after open_time on the same calendar day (no overnight ranges in MVP). Ranges on the same weekday MUST NOT overlap (half-open). Empty schedule means the room is closed every day.

On create, a room MUST start with **no ranges** until configured in **Horarios**.

Admin MUST set the schedule via a **Horarios** modal: add day + range into a list (grid), remove rows, then save full replace via API.

#### Scenario: Save two Monday ranges
- **GIVEN** a room with empty schedule
- **WHEN** admin adds Monday 08:00–12:00 and Monday 16:00–21:00 and saves Horarios
- **THEN** GET room hours MUST return both Monday ranges
- **AND** other weekdays MUST have no ranges

#### Scenario: Same-day overlapping ranges rejected
- **GIVEN** admin builds Monday 08:00–13:00 and Monday 12:00–18:00
- **WHEN** they save Horarios
- **THEN** the response MUST be `422`

### Requirement: Open hours exclusive among active rooms of the same site

When saving room weekly hours (`PUT …/rooms/{id}/hours`), the system MUST reject the schedule if any open weekday range of this room overlaps another **active** room’s open range on the same weekday within the **same site**. Overlap MUST use half-open intervals `[open_time, close_time)` (so 09:00–12:00 and 12:00–21:00 MUST NOT conflict). Inactive rooms MUST be ignored. Rooms of other sites MUST be ignored.

#### Scenario: Overlapping open windows rejected
- **GIVEN** room A (active) at site S open Monday 09:00–13:00
- **AND** room B (active) at site S
- **WHEN** admin saves B as open Monday 12:00–18:00
- **THEN** the response MUST be `422` and B’s previous hours MUST remain unchanged

#### Scenario: Adjacent open windows accepted
- **GIVEN** room A (active) at site S open Monday 09:00–12:00
- **AND** room B (active) at site S
- **WHEN** admin saves B as open Monday 12:00–21:00
- **THEN** the schedule MUST be saved

#### Scenario: Inactive peer ignored
- **GIVEN** room A (inactive) at site S open Monday 09:00–18:00
- **AND** room B (active) at site S
- **WHEN** admin saves B as open Monday 10:00–12:00
- **THEN** the schedule MUST be saved

### Requirement: Series must fit room open hours

When creating (or updating) a class series, the system MUST reject the request if the room has no open range on that weekday, or if the class half-open interval `[start_time, start_time + duration_minutes)` is not fully contained in **at least one** open range for that weekday.

#### Scenario: Series on closed day rejected
- **GIVEN** a room with no open ranges
- **WHEN** admin creates a series for that room
- **THEN** the response MUST be `422`

#### Scenario: Series outside all open ranges rejected
- **GIVEN** room open Monday 09:00–12:00 and 16:00–20:00
- **WHEN** admin creates a Monday series at 11:00 lasting 90 minutes
- **THEN** the response MUST be `422`

#### Scenario: Series inside second range accepted
- **GIVEN** room open Monday 08:00–12:00 and 16:00–21:00 and capacity sufficient
- **WHEN** admin creates Monday series 18:00 duration 60 at free room slot
- **THEN** the series MUST be created

## MODIFIED Requirements

### Requirement: Salones CRUD

Admin MUST be able to create, update, and soft-deactivate salones with: site, name, physical capacity, **default_class_duration_minutes**, and active flag. The Salones admin list MUST expose **Editar** and **Horarios** actions per room (labels and button styling as design).

#### Scenario: Create room requires duration
- **GIVEN** an admin
- **WHEN** they create a room with name, capacity, site, and duration
- **THEN** the room MUST persist and appear in the Salones list

## Out of scope (this change)
- Overnight open ranges
- Mass-cancel of existing series when hours shrink
- Prefilling Series form from room defaults
- Alumno/instructor editing rooms
