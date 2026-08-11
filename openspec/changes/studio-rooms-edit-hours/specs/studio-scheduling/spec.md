# Delta: Studio Scheduling — room hours enforcement

## ADDED Requirements

### Requirement: Room hours bound series times

Class series create/update MUST be validated against the assigned room’s weekly open hours (see `studio-sites`). Closed weekday or class interval not contained in the open range MUST fail with `422` and a non-secret error detail suitable for UI display.

#### Scenario: Overlap still checked after hours pass
- **GIVEN** a valid in-hours series slot that overlaps another series in the same room
- **WHEN** admin creates the second series
- **THEN** the system MUST still reject due to room time overlap (existing rule)

## Out of scope
- Re-validating all historical series after hours edit
