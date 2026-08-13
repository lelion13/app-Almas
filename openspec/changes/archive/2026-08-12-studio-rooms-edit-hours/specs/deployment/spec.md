# Delta: Deployment — Alembic head 010

## MODIFIED Requirements

### Requirement: Migrations

Backend entrypoint MUST run `alembic upgrade head` unless `SKIP_DB_MIGRATE=1`. Product Alembic head MUST be **`010`**.

Chain: `003`/`004` MP accounts + `005_studio_ops` + `006_site_maps_url` + `007_room_hours` + `008_room_hour_slots` + `009_room_share_space` + `010_ensure_room_share_space`.

`010` MUST be idempotent: add `studio_rooms.shares_space_with_room_id` if missing; drop leftover `space_id` / `studio_spaces` from the abandoned Espacios design. Operators MUST NOT assume stamp `009` means the share-space column exists (revision file was rewritten in place).

#### Scenario: Fresh deploy applies studio room hours
- **GIVEN** an empty database and images containing studio migrations
- **WHEN** backend starts with migrate enabled
- **THEN** Alembic MUST reach head `010` including room duration, multi-slot hours, and `shares_space_with_room_id`

#### Scenario: Upgrade from rewritten 009 stamp
- **GIVEN** a database with `alembic_version = 009` and `studio_rooms.space_id` but no `shares_space_with_room_id`
- **WHEN** backend starts with migrate enabled on an image that includes `010`
- **THEN** Alembic MUST apply `010` adding `shares_space_with_room_id` and removing leftover space catalog columns/tables
