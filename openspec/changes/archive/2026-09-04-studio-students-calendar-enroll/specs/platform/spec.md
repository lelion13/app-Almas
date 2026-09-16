# Delta: Platform — calendar enroll under pause

## MODIFIED Requirements

### Requirement: Studio schedule pause flag

While pause is enabled, Estudio Calendario carve-outs MUST include:
- `GET /api/v1/studio/calendar/availability`
- `POST /api/v1/studio/calendar/schedule`
- `POST /api/v1/studio/calendar/enroll`

#### Scenario: Enroll works while paused
- **GIVEN** `STUDIO_SCHEDULE_PAUSED=true`
- **WHEN** admin calls calendar enroll
- **THEN** the response MUST NOT be `410` solely due to the pause gate
