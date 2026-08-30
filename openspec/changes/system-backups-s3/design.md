# Design: system-backups-s3

## Technical Approach
Implement an end-to-end backup subsystem with:
1. **Engine**: Subprocess execution of `pg_dump -Fc` with credentials parsed from `DATABASE_URL`, writing to a secured temp file.
2. **S3 Storage Client**: Universal S3 client wrapper (`boto3` / `botocore`) supporting custom endpoints (Cloudflare R2, AWS S3, MinIO, Backblaze B2) and multipart/stream uploads.
3. **Retention Manager**: List bucket objects matching the configured prefix, sort by timestamp, and delete objects exceeding `retention_count`.
4. **Internal Scheduler**: APScheduler `AsyncIOScheduler` initialized on FastAPI startup, executing background jobs and dynamic rescheduling when admin saves updated frequency/time.
5. **State & Auditing**: DB tables `system_backup_config` (singleton configuration) and `system_backup_logs` (execution history).
6. **Admin UI**: Dedicated page `/configuracion` in React with status cards, manual run button, schedule/S3 form, and history table.

## Architecture Decisions

| Decision | Choice | Alternatives Considered | Rationale |
|----------|--------|-------------------------|-----------|
| **Dump format** | `pg_dump -Fc` (custom binary compressed) | `.sql.gz`, raw CSVs | Native PostgreSQL binary format supports selective restore, compression, and direct compatibility with `pg_restore`. |
| **Cloud Storage** | Universal S3 API via `boto3` | Google Drive API, rclone, local disk | S3 is the industry standard, supported by AWS, Cloudflare R2 (zero egress fees), Wasabi, MinIO, and Backblaze B2. |
| **Scheduler Engine** | APScheduler (`AsyncIOScheduler`) | OS cron, external webhook, Celery | Self-contained within FastAPI process, zero extra infrastructure (no Redis needed), dynamic schedule updates via UI. |
| **Concurrency Control** | In-memory async Lock (`asyncio.Lock`) | DB distributed lock, Redis | Ensures only one backup job runs at any given moment, preventing server resource starvation. |

## Data Flow

```
[ Admin UI / APScheduler ]
             │
             ▼
    [ BackupService.run_backup() ] ──(Acquire Lock)
             │
             ├── 1. Execute `pg_dump -Fc` → /tmp/backup_YYYYMMDD_HHMMSS.dump
             │
             ├── 2. S3Client.upload_file() ──→ [ External S3 Bucket (R2/AWS) ]
             │
             ├── 3. S3Client.prune_retention() (Delete oldest exceeding N)
             │
             ├── 4. DB Insert → `system_backup_logs` (status, size, key, duration)
             │
             └── 5. Cleanup local temp file & Release Lock
```

## Database Schema (Alembic 012)

### Table `system_backup_config`
- `id`: `Integer` primary key (singleton row `id=1`)
- `enabled`: `Boolean` (default `False`)
- `schedule_type`: `String` (e.g., `"daily"`, `"weekly"`)
- `schedule_time`: `String` (e.g., `"03:00"`)
- `schedule_day_of_week`: `Integer` nullable (`0-6` for weekly)
- `s3_endpoint_url`: `String` nullable (e.g. `https://<account_id>.r2.cloudflarestorage.com`)
- `s3_bucket_name`: `String`
- `s3_region_name`: `String` default `"auto"`
- `s3_access_key_id`: `String`
- `s3_secret_access_key`: `String` (encrypted at rest or masked in UI)
- `s3_prefix`: `String` default `"almas-backups/"`
- `retention_count`: `Integer` default `15`
- `updated_at`: `DateTime(timezone=True)`

### Table `system_backup_logs`
- `id`: `UUID` primary key
- `trigger_type`: `String` (`"manual"`, `"scheduled"`)
- `status`: `String` (`"running"`, `"success"`, `"failed"`)
- `file_name`: `String`
- `file_size_bytes`: `BigInteger` nullable
- `storage_key`: `String` nullable
- `duration_seconds`: `Float` nullable
- `error_message`: `Text` nullable
- `started_at`: `DateTime(timezone=True)`
- `completed_at`: `DateTime(timezone=True)` nullable

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/Dockerfile` | Modify | Add `postgresql-client` to `apt-get install` |
| `backend/requirements.txt` | Modify | Add `boto3`, `apscheduler` |
| `backend/alembic/versions/012_system_backups.py` | Create | Migration creating backup config and logs tables |
| `backend/app/models/backup.py` | Create | SQLAlchemy models `SystemBackupConfig`, `SystemBackupLog` |
| `backend/app/models/__init__.py` | Modify | Export backup models |
| `backend/app/schemas/backup.py` | Create | Pydantic schemas for config, manual trigger, logs |
| `backend/app/services/backup_service.py` | Create | Core dump, S3 upload, retention, and lock logic |
| `backend/app/services/scheduler_service.py` | Create | APScheduler wrapper and job registration |
| `backend/app/api/routers/backup.py` | Create | Endpoints `/api/v1/backups/*` (admin-only) |
| `backend/app/api/router.py` | Modify | Register backup router |
| `backend/app/main.py` | Modify | Add lifespan / startup event to initialize scheduler |
| `frontend/src/services/api.ts` | Modify | Add typed API methods for backups |
| `frontend/src/pages/SettingsBackupPage.tsx` | Create | Settings & Backup management page |
| `frontend/src/components/AppShell.tsx` | Modify | Add "Configuración" link for admin role |
| `frontend/src/App.tsx` | Modify | Register `/configuracion` route |
| `backend/tests/test_backups.py` | Create | Unit tests for backup schemas, retention math, S3 mock |

## Testing Strategy
- **Unit**: Test Pydantic schemas, S3 path normalization, retention sorting & deletion algorithm, and database models.
- **Integration**: Test `/api/v1/backups/*` endpoints with admin and non-admin auth tokens (403 verification).
- **Subprocess Mocking**: Mock `pg_dump` and `boto3` client in pytest to verify end-to-end execution flow and error logging.
