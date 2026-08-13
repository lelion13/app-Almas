# Delta: Studio Scheduling — room hours enforcement

## ADDED Requirements

### Requirement: Room hours bound series times

Class series create/update MUST be validated against the assigned room’s weekly open hours (see `studio-sites`). No open ranges on the weekday, or class interval not fully contained in **at least one** open range, MUST fail with `422` and a non-secret error detail suitable for UI display.

#### Scenario: Overlap still checked after hours pass
- **GIVEN** a valid in-hours series slot that overlaps another series in the same room
- **WHEN** admin creates the second series
- **THEN** the system MUST still reject due to room time overlap (existing rule)

### Requirement: Series overlap includes shared-space peer

Two **active** series MUST NOT overlap on the same weekday when they belong to the same room **or** to rooms linked by `shares_space_with_room_id`. Unlinked rooms in the same site MAY have overlapping series.

#### Scenario: Shared-space series overlap rejected
- **GIVEN** Yoga shares space with Postural
- **AND** Yoga has an active Monday series 10:00 duration 60
- **WHEN** admin creates a Postural Monday series 10:30 duration 60
- **THEN** the system MUST reject with validation error

## Out of scope
- Re-validating all historical series after hours edit
