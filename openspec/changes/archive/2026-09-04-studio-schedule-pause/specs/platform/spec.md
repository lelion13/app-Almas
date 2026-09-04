# Delta: Platform — schedule pause flag

## ADDED Requirements

### Requirement: Studio schedule pause flag

The backend MUST read `STUDIO_SCHEDULE_PAUSED` from environment (boolean; default **true** for this change). When true, paused studio schedule/pack/booking routes MUST return 410. When false, previous behavior MUST resume without schema changes.

`.env.example` / `.env.prod.example` MUST document the variable.

#### Scenario: Flag off restores APIs
- **GIVEN** `STUDIO_SCHEDULE_PAUSED=false`
- **WHEN** admin calls `GET /api/v1/studio/series`
- **THEN** the response MUST NOT be `410` solely due to the pause gate
