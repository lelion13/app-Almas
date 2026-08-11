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

Each salón MUST support a weekly schedule of up to one open time range per weekday (0–6). For each weekday admin can mark open/closed; if open, open_time and close_time are required and close_time MUST be after open_time same calendar day (no overnight ranges in MVP).

On create, a room MUST start with **no open days** (all closed / empty schedule) until configured in **Horarios**.

Admin MUST set the schedule via a **Horarios** action modal that saves the full week (replace).

#### Scenario: Save open Monday
- **GIVEN** a room with empty schedule
- **WHEN** admin sets Monday open 08:00–21:00 and saves Horarios
- **THEN** GET room hours MUST include Monday open with that range
- **AND** other weekdays MUST remain closed

#### Scenario: Closed weekday has no times
- **GIVEN** a weekday marked closed
- **WHEN** schedule is saved
- **THEN** open_time and close_time MUST be null for that weekday

### Requirement: Series must fit room open hours

When creating (or updating) a class series, the system MUST reject the request if the room is closed on that weekday, or if the class half-open interval `[start_time, start_time + duration_minutes)` is not fully contained in the room’s open range for that weekday.

#### Scenario: Series on closed day rejected
- **GIVEN** a room with no open weekdays
- **WHEN** admin creates a series for that room
- **THEN** the response MUST be `422`

#### Scenario: Series outside open range rejected
- **GIVEN** room open Monday 09:00–12:00
- **WHEN** admin creates a Monday series at 11:00 lasting 90 minutes
- **THEN** the response MUST be `422`

#### Scenario: Series inside open range accepted
- **GIVEN** room open Monday 08:00–21:00 and capacity sufficient
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
- Multiple open ranges per weekday
- Prefilling Series form from room defaults
- Overnight open ranges
- Mass-cancel of existing series when hours shrink
- Alumno/instructor editing rooms
