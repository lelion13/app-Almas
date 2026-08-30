import asyncio
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import subprocess
import tempfile
import time
from uuid import uuid4

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import desc, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.backup import SystemBackupConfig, SystemBackupLog
from app.schemas.backup import BackupConfigUpdate

logger = logging.getLogger(__name__)

_backup_lock = asyncio.Lock()


def is_backup_running() -> bool:
    return _backup_lock.locked()


def get_or_create_config(db: Session) -> SystemBackupConfig:
    stmt = select(SystemBackupConfig).where(SystemBackupConfig.id == 1)
    config = db.scalar(stmt)
    if not config:
        config = SystemBackupConfig(
            id=1,
            enabled=False,
            schedule_type="daily",
            schedule_time="03:00",
            schedule_day_of_week=None,
            s3_endpoint_url=None,
            s3_bucket_name="",
            s3_region_name="auto",
            s3_access_key_id="",
            s3_secret_access_key="",
            s3_prefix="almas-backups/",
            retention_count=15,
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def update_config(db: Session, update_data: BackupConfigUpdate) -> SystemBackupConfig:
    config = get_or_create_config(db)
    config.enabled = update_data.enabled
    config.schedule_type = update_data.schedule_type
    config.schedule_time = update_data.schedule_time
    config.schedule_day_of_week = update_data.schedule_day_of_week
    config.s3_endpoint_url = update_data.s3_endpoint_url.strip() if update_data.s3_endpoint_url else None
    config.s3_bucket_name = update_data.s3_bucket_name.strip()
    config.s3_region_name = update_data.s3_region_name.strip() or "auto"
    config.s3_access_key_id = update_data.s3_access_key_id.strip()
    if update_data.s3_secret_access_key and update_data.s3_secret_access_key.strip():
        config.s3_secret_access_key = update_data.s3_secret_access_key.strip()
    config.s3_prefix = update_data.s3_prefix.strip() or "almas-backups/"
    config.retention_count = update_data.retention_count
    db.commit()
    db.refresh(config)
    return config


def list_logs(db: Session, limit: int = 50) -> list[SystemBackupLog]:
    stmt = select(SystemBackupLog).order_by(desc(SystemBackupLog.started_at)).limit(limit)
    return list(db.scalars(stmt).all())


def get_last_log(db: Session) -> SystemBackupLog | None:
    stmt = select(SystemBackupLog).order_by(desc(SystemBackupLog.started_at)).limit(1)
    return db.scalar(stmt)


def _get_s3_client(config: SystemBackupConfig):
    if not config.s3_bucket_name or not config.s3_access_key_id or not config.s3_secret_access_key:
        raise ValueError("S3 bucket, Access Key ID, and Secret Access Key must be configured.")

    boto_cfg = BotoConfig(
        signature_version="s3v4",
        retries={"max_attempts": 3, "mode": "standard"},
    )
    return boto3.client(
        "s3",
        endpoint_url=config.s3_endpoint_url if config.s3_endpoint_url else None,
        aws_access_key_id=config.s3_access_key_id,
        aws_secret_access_key=config.s3_secret_access_key,
        region_name=config.s3_region_name or "auto",
        config=boto_cfg,
    )


def prune_s3_backups(s3_client, bucket_name: str, prefix: str, retention_count: int) -> int:
    if retention_count < 1:
        return 0

    clean_prefix = prefix.strip("/") + "/" if prefix.strip("/") else ""
    paginator = s3_client.get_paginator("list_objects_v2")
    objects = []
    for page in paginator.paginate(Bucket=bucket_name, Prefix=clean_prefix):
        for item in page.get("Contents", []):
            key = item.get("Key", "")
            if key.endswith(".dump"):
                objects.append(item)

    objects.sort(key=lambda x: x["LastModified"])

    deleted_count = 0
    if len(objects) > retention_count:
        to_delete = objects[: len(objects) - retention_count]
        delete_keys = [{"Key": obj["Key"]} for obj in to_delete]
        if delete_keys:
            s3_client.delete_objects(Bucket=bucket_name, Delete={"Objects": delete_keys})
            deleted_count = len(delete_keys)
            logger.info("Pruned %d old backups from S3 bucket %s", deleted_count, bucket_name)
    return deleted_count


def _run_pg_dump(temp_dump_path: Path):
    db_url = make_url(settings.database_url)
    host = db_url.host or "127.0.0.1"
    port = str(db_url.port or 5432)
    username = db_url.username or "postgres"
    password = db_url.password or ""
    database = db_url.database or "almas"

    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password

    cmd = [
        "pg_dump",
        "-Fc",
        "-h",
        host,
        "-p",
        port,
        "-U",
        username,
        "-d",
        database,
        "-f",
        str(temp_dump_path),
    ]

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        err = result.stderr.strip() or f"pg_dump failed with exit code {result.returncode}"
        raise RuntimeError(f"Error executing pg_dump: {err}")


def _execute_backup_sync(trigger_type: str, log_id) -> SystemBackupLog:
    db = SessionLocal()
    start_time = time.time()
    now_utc = datetime.now(timezone.utc)
    timestamp_str = now_utc.strftime("%Y%m%d_%H%M%S")
    file_name = f"almas_backup_{timestamp_str}.dump"

    log = SystemBackupLog(
        id=log_id,
        trigger_type=trigger_type,
        status="running",
        file_name=file_name,
        started_at=now_utc,
    )
    db.add(log)
    db.commit()

    temp_file = None
    try:
        config = get_or_create_config(db)
        if not config.s3_bucket_name or not config.s3_access_key_id or not config.s3_secret_access_key:
            raise ValueError("Configuración S3 incompleta (bucket, access key y secret son requeridos).")

        temp_dir = tempfile.gettempdir()
        temp_file = Path(temp_dir) / f"{file_name}_{uuid4().hex[:8]}"

        _run_pg_dump(temp_file)

        if not temp_file.exists():
            raise FileNotFoundError("El archivo de dump no fue generado.")

        file_size = temp_file.stat().st_size

        s3_client = _get_s3_client(config)
        clean_prefix = config.s3_prefix.strip("/") + "/" if config.s3_prefix.strip("/") else ""
        storage_key = f"{clean_prefix}{file_name}"

        with open(temp_file, "rb") as f:
            s3_client.upload_fileobj(f, config.s3_bucket_name, storage_key)

        prune_s3_backups(s3_client, config.s3_bucket_name, config.s3_prefix, config.retention_count)

        duration = round(time.time() - start_time, 2)
        log.status = "success"
        log.file_size_bytes = file_size
        log.storage_key = storage_key
        log.duration_seconds = duration
        log.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(log)
        logger.info("Backup %s completed successfully in %.2fs (%d bytes)", file_name, duration, file_size)
        return log

    except Exception as e:
        duration = round(time.time() - start_time, 2)
        err_msg = str(e)
        logger.error("Backup %s failed: %s", file_name, err_msg, exc_info=True)
        log.status = "failed"
        log.duration_seconds = duration
        log.error_message = err_msg
        log.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(log)
        return log

    finally:
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass
        db.close()


async def execute_backup(trigger_type: str = "manual") -> SystemBackupLog:
    if _backup_lock.locked():
        raise RuntimeError("Ya hay una tarea de backup en ejecución.")

    async with _backup_lock:
        log_id = uuid4()
        log = await asyncio.to_thread(_execute_backup_sync, trigger_type, log_id)
        return log
