# Proposal: system-backups-s3

## Intent
Provide automated and manual database backup capabilities directly from the application's Admin UI, uploading compressed binary dumps (`pg_dump -Fc`) to external S3-compatible cloud storage (e.g., Cloudflare R2, AWS S3, MinIO) with configurable retention policies and execution history.

## Scope

### In Scope
- **Backend Service & Engine**:
  - Integrate `boto3` / `botocore` for S3-compatible object storage operations (upload, list, delete/rotate).
  - Background task / internal scheduler (APScheduler / FastAPI background scheduler) for cron-like automated backups.
  - Backup execution via `pg_dump -Fc` subprocess with database connection stream and temporary file or buffered pipe.
  - Database table `system_backup_logs` to record history (timestamp, trigger type `manual`|`scheduled`, status `success`|`failed`, size_bytes, storage_key, error_message).
  - Database settings table or singleton `system_backup_config` (enabled, cron/schedule expression or hour/frequency, s3 bucket, endpoint, prefix, retention_count/days).
- **API (Admin only)**:
  - `GET /api/v1/backups/config`: Retrieve backup configuration and destination settings.
  - `PUT /api/v1/backups/config`: Update backup schedule, S3 destination, and retention policy.
  - `POST /api/v1/backups/run`: Trigger immediate manual backup.
  - `GET /api/v1/backups/logs`: List backup execution history.
- **Frontend UI**:
  - Menu option under Admin / AppShell: **Configuración** (`/configuracion` or `/settings`).
  - Section for **Backups de Base de Datos**:
    - Trigger button: "Realizar backup ahora" with live progress / status alert.
    - Configuration card: S3 credentials / bucket / endpoint URL / prefix path, schedule (enabled, daily hour / frequency), retention count.
    - Backup history table: date, trigger, file size, status, S3 key, error detail if failed.
- **Docker / VPS Packaging**:
  - Ensure `postgresql-client` (providing `pg_dump`) is installed in backend Docker image.

### Out of Scope
- Direct database restore via web UI (restore must follow safe CLI runbook `pg_restore` to avoid accidental production data overwrite).
- Non-S3 custom protocol plugins (focus specifically on universal S3-compatible API).
- Non-admin access to backup endpoints or configuration.

## Approach
1. **Container Tooling**: Add `postgresql-client` to `backend/Dockerfile` so `pg_dump` is available to the FastAPI runtime container.
2. **Configuration & Persistence**: Create Alembic migration for `system_backup_config` and `system_backup_logs`.
3. **Execution Pipeline**:
   - Dump generated locally to a secure temp path using `pg_dump -Fc` using configured database connection parameters.
   - Upload file to configured S3 bucket using `boto3`.
   - Apply retention rotation (delete oldest backups in S3 exceeding retention count/days).
   - Write execution result to `system_backup_logs`.
   - Clean up local temp file.
4. **Scheduler**: FastAPI startup lifecycle event initializes APScheduler / async background scheduler reading schedule from `system_backup_config`.
5. **UI**: Add **Configuración** route in frontend with clean, mobile-first cards for trigger, S3 settings, and logs history.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/Dockerfile` | Modified | Add `postgresql-client` package |
| `backend/requirements.txt` | Modified | Add `boto3`, `apscheduler` |
| `backend/alembic/versions/012_system_backups.py` | New | Tables `system_backup_config`, `system_backup_logs` |
| `backend/app/models/backup.py` | New | SQLAlchemy models for config and logs |
| `backend/app/schemas/backup.py` | New | Pydantic schemas for config, triggers, logs |
| `backend/app/services/backup_service.py` | New | Dump execution, S3 upload, retention rotation, scheduler management |
| `backend/app/api/routers/backup.py` | New | Endpoints for backup operations and history |
| `frontend/src/pages/SettingsBackupPage.tsx` | New | Settings & Backup UI page |
| `frontend/src/components/AppShell.tsx` | Modified | Add "Configuración" navigation link for admin |
| `frontend/src/App.tsx` | Modified | Register `/configuracion` route |
| `openspec/specs/platform/spec.md` | Modified | Delta specs for system backup and settings |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `pg_dump` client version mismatch with PostgreSQL 18 server | Medium | Ensure Debian bookworm package / compatible client flags, test stream dump |
| S3 upload failure (invalid credentials / network timeout) | Medium | Catch errors, log failure in `system_backup_logs`, surface clear error in UI |
| Concurrent manual + scheduled backup runs | Low | Backend mutex / lock prevents running two backup jobs simultaneously |
| Large dump filling container disk space | Low | Fast streaming / immediate temp file cleanup in `finally` block |

## Rollback Plan
- Disable scheduler in config (`enabled = false`).
- Alembic downgrade `011` drops backup tables without affecting core business data (cierres, estudio, mp).

## Dependencies
- S3-compatible bucket & credentials provided by operator (Cloudflare R2 / AWS S3 / B2).

## Success Criteria
- [ ] Admin can trigger a manual backup from UI and see a successful record with file size in history.
- [ ] Backup file is present and valid in external S3 storage bucket.
- [ ] Scheduled cron job triggers automatically at the configured time and uploads backup.
- [ ] Old backups are pruned according to configured retention limit.
- [ ] Non-admin users cannot access configuration or trigger backups.
