# Delta: Platform — System Database Backups (S3 & Scheduler)

## ADDED Requirements

### Requirement: Database Backups to S3-Compatible Storage

The system MUST provide functionality for administrators to generate and export compressed PostgreSQL database backups (`pg_dump -Fc`) and store them in an external S3-compatible object storage provider (e.g. AWS S3, Cloudflare R2, MinIO).

Only users with `admin` role MUST be authorized to access backup configuration, view logs, or trigger backups.

#### Scenario: Admin triggers manual backup successfully
- **GIVEN** an authenticated admin and valid S3 destination configuration
- **WHEN** the admin requests a manual backup (`POST /api/v1/backups/run`)
- **THEN** the system MUST execute `pg_dump -Fc` against the PostgreSQL database
- **AND** upload the resulting dump to the configured S3 bucket and prefix
- **AND** record a `success` entry in the backup execution log
- **AND** remove any temporary files created locally

#### Scenario: Manual backup failure logged
- **GIVEN** an authenticated admin and invalid S3 credentials or unreachable network
- **WHEN** a backup execution is triggered
- **THEN** the system MUST capture the error without crashing the server
- **AND** record a `failed` entry with the error message in the backup execution log
- **AND** return an appropriate error status to the client

### Requirement: Scheduled Automated Backups

The system MUST support automated periodic backups executed by an internal background scheduler according to the schedule configured in the system settings.

#### Scenario: Scheduled backup execution
- **GIVEN** scheduled backups are enabled with a specific execution hour / interval
- **WHEN** the scheduled time arrives
- **THEN** the backend scheduler MUST initiate the backup pipeline in the background
- **AND** record the trigger type as `scheduled` in the backup log

### Requirement: Backup Retention & Pruning

The system MUST enforce a configurable retention policy on external storage.

#### Scenario: Pruning old backups exceeding retention limit
- **GIVEN** a backup completes successfully and the total stored backups exceed the configured retention limit N
- **WHEN** retention rotation executes
- **THEN** the oldest backup object(s) exceeding N MUST be deleted from the S3 bucket
- **AND** the log history updated accordingly

### Requirement: Settings and Configuration Management UI

The frontend MUST provide a **Configuración** menu for admin users with a dedicated section for Database Backups.

#### Scenario: View and edit backup configuration
- **GIVEN** an admin visiting `/configuracion`
- **WHEN** the admin loads the page
- **THEN** the current backup settings (enabled, schedule, bucket, endpoint, prefix, retention) and recent backup history MUST be displayed
- **AND** the admin MAY update settings and save them
