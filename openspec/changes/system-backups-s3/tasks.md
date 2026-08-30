# Tasks: system-backups-s3

## Phase 1: Infrastructure & Dependencies

- [x] 1.1 Add `boto3` and `apscheduler` to `backend/requirements.txt`
- [x] 1.2 Update `backend/Dockerfile` to install `postgresql-client` for `pg_dump`
- [x] 1.3 Create Alembic migration `012_system_backups.py` for `system_backup_config` and `system_backup_logs`
- [x] 1.4 Create SQLAlchemy models `backend/app/models/backup.py` and export in `backend/app/models/__init__.py`

## Phase 2: Backend Core Implementation

- [x] 2.1 Create Pydantic schemas in `backend/app/schemas/backup.py` (config, run trigger, logs, status)
- [x] 2.2 Implement `backend/app/services/backup_service.py` (`pg_dump` execution, S3 upload, retention pruning, concurrency lock)
- [x] 2.3 Implement `backend/app/services/scheduler_service.py` (APScheduler initialization and dynamic schedule reload)
- [x] 2.4 Create API router `backend/app/api/routers/backup.py` and wire into `backend/app/api/router.py`
- [x] 2.5 Hook scheduler into FastAPI startup/shutdown lifecycle in `backend/app/main.py`

## Phase 3: Frontend Implementation

- [x] 3.1 Add backup API methods to `frontend/src/services/api.ts`
- [x] 3.2 Create `frontend/src/pages/SettingsBackupPage.tsx` with S3 config form, manual trigger button, and history table
- [x] 3.3 Add "Configuración" link to `frontend/src/components/AppShell.tsx` for admin users
- [x] 3.4 Register route `/configuracion` in `frontend/src/App.tsx`

## Phase 4: Testing & Documentation

- [x] 4.1 Write unit & integration tests in `backend/tests/test_backups.py` (schemas, S3 mock, retention, role authorization)
- [x] 4.2 Verify backend test suite (`python -m pytest`) and frontend build (`npm run build`)
- [x] 4.3 Update runbook and deployment docs (`docs/runbook.md`, `docs/vps-deploy.md`) with S3 backup setup instructions

## Dependencies
- Phase 1 before Phase 2.
- Phase 2 before Phase 3 and Phase 4.
