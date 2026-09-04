# Delta: Deployment — Alembic head 013

## MODIFIED Requirements

### Requirement: Migrations

Product Alembic head MUST be **`013`**.

Chain: … `012_system_backups` + `013_instructor_activities`.

`013` MUST create `studio_instructor_activities` (`instructor_id`, `activity_id`, unique pair). It MUST NOT invent activity links for existing instructors.

#### Scenario: Fresh deploy includes instructor activities junction
- **GIVEN** an empty database and images containing studio migrations
- **WHEN** backend starts with migrate enabled
- **THEN** Alembic MUST reach head `013` including `studio_instructor_activities`

#### Scenario: Upgrade from 012 leaves old instructors unlinked
- **GIVEN** a database at head `012` with existing `studio_instructors` rows
- **WHEN** `013` applies
- **THEN** those instructors MUST have zero junction rows until an admin assigns activities
