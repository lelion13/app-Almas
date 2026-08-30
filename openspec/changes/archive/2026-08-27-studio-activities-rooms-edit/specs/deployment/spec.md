# Delta: Deployment — Alembic head 011

## MODIFIED Requirements

### Requirement: Migrations

Backend entrypoint MUST run `alembic upgrade head` unless `SKIP_DB_MIGRATE=1`. Product Alembic head MUST be **`011`**.

Chain: … `010_ensure_room_share_space` + `011_activity_rooms`.

`011` MUST create `studio_activity_rooms` (activity_id, room_id, unique pair). It MUST NOT invent room links for existing activities.

#### Scenario: Fresh deploy includes activity rooms
- **GIVEN** an empty database and images containing studio migrations
- **WHEN** backend starts with migrate enabled
- **THEN** Alembic MUST reach head `011` including `studio_activity_rooms`

#### Scenario: Upgrade from 010 leaves old activities unlinked
- **GIVEN** a database at head `010` with existing `studio_activities` rows
- **WHEN** `011` applies
- **THEN** those activities MUST have zero junction rows until an admin assigns rooms
