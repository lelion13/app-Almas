from datetime import datetime, timezone
from unittest.mock import MagicMock
import uuid

import pytest
from pydantic import ValidationError

from app.models.backup import SystemBackupConfig, SystemBackupLog
from app.schemas.backup import (
    BackupConfigResponse,
    BackupConfigUpdate,
    BackupLogResponse,
    BackupRunResponse,
    BackupStatusResponse,
)
from app.services.backup_service import (
    _get_s3_client,
    is_backup_running,
    prune_s3_backups,
)


def test_backup_config_schema_validation():
    cfg = BackupConfigUpdate(
        enabled=True,
        schedule_type="daily",
        schedule_time="04:30",
        s3_bucket_name="my-backup-bucket",
        s3_access_key_id="ACCESS123",
        retention_count=20,
    )
    assert cfg.enabled is True
    assert cfg.schedule_time == "04:30"
    assert cfg.retention_count == 20
    assert cfg.s3_prefix == "almas-backups/"


def test_backup_config_schema_rejects_invalid_retention():
    with pytest.raises(ValidationError):
        BackupConfigUpdate(
            s3_bucket_name="test",
            s3_access_key_id="key",
            retention_count=0,
        )

    with pytest.raises(ValidationError):
        BackupConfigUpdate(
            s3_bucket_name="test",
            s3_access_key_id="key",
            retention_count=500,
        )


def test_prune_s3_backups_deletes_oldest_when_exceeding_retention():
    mock_s3 = MagicMock()
    mock_paginator = MagicMock()
    mock_s3.get_paginator.return_value = mock_paginator

    # 4 backup items, retention_count = 2 -> should delete 2 oldest
    mock_paginator.paginate.return_value = [
        {
            "Contents": [
                {"Key": "almas-backups/backup_20260101_000000.dump", "LastModified": datetime(2026, 1, 1, tzinfo=timezone.utc)},
                {"Key": "almas-backups/backup_20260102_000000.dump", "LastModified": datetime(2026, 1, 2, tzinfo=timezone.utc)},
                {"Key": "almas-backups/backup_20260103_000000.dump", "LastModified": datetime(2026, 1, 3, tzinfo=timezone.utc)},
                {"Key": "almas-backups/backup_20260104_000000.dump", "LastModified": datetime(2026, 1, 4, tzinfo=timezone.utc)},
                {"Key": "almas-backups/other_file.txt", "LastModified": datetime(2026, 1, 5, tzinfo=timezone.utc)},
            ]
        }
    ]

    deleted = prune_s3_backups(mock_s3, "my-bucket", "almas-backups/", retention_count=2)
    assert deleted == 2
    mock_s3.delete_objects.assert_called_once_with(
        Bucket="my-bucket",
        Delete={
            "Objects": [
                {"Key": "almas-backups/backup_20260101_000000.dump"},
                {"Key": "almas-backups/backup_20260102_000000.dump"},
            ]
        },
    )


def test_prune_s3_backups_noop_when_within_retention():
    mock_s3 = MagicMock()
    mock_paginator = MagicMock()
    mock_s3.get_paginator.return_value = mock_paginator

    mock_paginator.paginate.return_value = [
        {
            "Contents": [
                {"Key": "almas-backups/backup_20260101_000000.dump", "LastModified": datetime(2026, 1, 1, tzinfo=timezone.utc)},
            ]
        }
    ]

    deleted = prune_s3_backups(mock_s3, "my-bucket", "almas-backups/", retention_count=5)
    assert deleted == 0
    mock_s3.delete_objects.assert_not_called()


def test_get_s3_client_raises_when_unconfigured():
    cfg = SystemBackupConfig(
        id=1,
        s3_bucket_name="",
        s3_access_key_id="",
        s3_secret_access_key="",
    )
    with pytest.raises(ValueError, match="S3 bucket, Access Key ID, and Secret Access Key must be configured"):
        _get_s3_client(cfg)


def test_backup_models_and_schemas_mapping():
    log_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    log = SystemBackupLog(
        id=log_id,
        trigger_type="manual",
        status="success",
        file_name="almas_backup_20260830_120000.dump",
        file_size_bytes=1048576,
        storage_key="almas-backups/almas_backup_20260830_120000.dump",
        duration_seconds=3.45,
        started_at=now,
        completed_at=now,
    )

    resp = BackupLogResponse.model_validate(log)
    assert resp.id == log_id
    assert resp.status == "success"
    assert resp.file_size_bytes == 1048576
    assert resp.duration_seconds == 3.45

    run_resp = BackupRunResponse(success=True, message="OK", log=resp)
    assert run_resp.success is True

    status_resp = BackupStatusResponse(is_running=is_backup_running(), last_log=resp, next_run_at=None)
    assert status_resp.is_running is False
    assert status_resp.last_log.id == log_id
