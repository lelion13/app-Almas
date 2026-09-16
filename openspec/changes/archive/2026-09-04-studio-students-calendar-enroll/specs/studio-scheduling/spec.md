# Delta: Studio Scheduling — calendar enroll carve-out

## MODIFIED Requirements

### Requirement: Schedule stack pause

In addition to existing calendar availability/schedule carve-outs, `POST /api/v1/studio/calendar/enroll` MUST NOT return `410` solely due to `STUDIO_SCHEDULE_PAUSED`.

#### Scenario: Calendar enroll carve-out under pause
- **GIVEN** pause enabled
- **WHEN** admin calls `POST /api/v1/studio/calendar/enroll`
- **THEN** the response MUST NOT be `410` solely due to the pause gate

### Requirement: Calendar slot instructor assignment

When a slot already has `series_id`, the slot modal MUST also allow assigning students for the selected date subject to capacity (see `studio-students`). Assigned slots MUST expose booked/remaining capacity for UI.

#### Scenario: Capacity on assigned slot
- **GIVEN** an assigned series slot
- **WHEN** availability is loaded
- **THEN** the slot MUST include enough data for the UI to know remaining capacity (e.g. `booked_count` and `capacity`)
