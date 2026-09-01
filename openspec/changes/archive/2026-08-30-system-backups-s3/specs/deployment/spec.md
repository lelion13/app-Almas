# Delta: Deployment — Database Backups & Container Tooling

## MODIFIED Requirements

### Requirement: Migrations

Backend entrypoint MUST run `alembic upgrade head` unless `SKIP_DB_MIGRATE=1`. Product Alembic head MUST be **`012`**.

Chain: … `011_activity_rooms` + `012_system_backups`.

`012` MUST create `system_backup_config` and `system_backup_logs` tables.

#### Scenario: Fresh deploy includes backup tables
- **GIVEN** an empty database and images containing migrations
- **WHEN** backend starts with migrate enabled
- **THEN** Alembic MUST reach head `012` including `system_backup_config` and `system_backup_logs`

## ADDED Requirements

### Requirement: Backend Container Backup Utilities

The backend Docker image MUST include `postgresql-client` (or equivalent package containing `pg_dump`) to enable database dump creation from within the application container.

#### Scenario: Backend container has pg_dump binary
- **GIVEN** the production backend container
- **WHEN** the backup process invokes `pg_dump`
- **THEN** the command MUST be executable without missing binary errors
