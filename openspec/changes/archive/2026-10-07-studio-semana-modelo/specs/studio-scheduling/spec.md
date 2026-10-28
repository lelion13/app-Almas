## ADDED Requirements

### Requirement: Semana modelo grid

Admin or instructor MUST manage a model week per room×activity. Cells MUST be generated from room hours tiled by activity duration (same tiling as calendar). Cupo MUST equal room capacity. Each filled cell MUST store instructor_id and student assignments (≤ capacity).

Clearing a cell (empty student_ids) MUST delete the model-week slot and its student links. Clearing MUST NOT cascade to existing abonos, ClassSeries, or calendar bookings.

#### Scenario: Load grid for room and activity
- **GIVEN** an active room with hours and an activity linked to that room
- **WHEN** `GET /studio/model-week?room_id&activity_id`
- **THEN** the response MUST list tiled cells with capacity and any stored instructor/students

#### Scenario: Put students on a cell
- **GIVEN** a valid tiled start_time for that weekday
- **WHEN** `PUT /studio/model-week/slot` with instructor and student_ids
- **THEN** the slot MUST be upserted and students replaced as a set

#### Scenario: Clear cell without cascade
- **GIVEN** a filled model-week slot linked historically to an abono
- **WHEN** the slot is cleared
- **THEN** the slot MUST be removed and existing abono/calendar data MUST remain

### Requirement: Instructor access to model week

Instructors MUST read catalog lists needed for the grid (sites, rooms, activities, instructors, students) and MUST edit any room×activity model week (not limited to their own activities for room selection; instructor assigned to a cell MUST still be linked to that activity).
