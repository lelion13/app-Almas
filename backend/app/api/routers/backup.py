from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import AdminOnly, get_db
from app.schemas.backup import (
    BackupConfigResponse,
    BackupConfigUpdate,
    BackupLogResponse,
    BackupRunResponse,
    BackupStatusResponse,
)
from app.services import backup_service
from app.services import scheduler_service

router = APIRouter()


def _to_config_response(cfg) -> BackupConfigResponse:
    return BackupConfigResponse(
        enabled=cfg.enabled,
        schedule_type=cfg.schedule_type,
        schedule_time=cfg.schedule_time,
        schedule_day_of_week=cfg.schedule_day_of_week,
        s3_endpoint_url=cfg.s3_endpoint_url,
        s3_bucket_name=cfg.s3_bucket_name,
        s3_region_name=cfg.s3_region_name,
        s3_access_key_id=cfg.s3_access_key_id,
        has_secret_access_key=bool(cfg.s3_secret_access_key and cfg.s3_secret_access_key.strip()),
        s3_prefix=cfg.s3_prefix,
        retention_count=cfg.retention_count,
        updated_at=cfg.updated_at,
    )


@router.get("/config", response_model=BackupConfigResponse)
def get_backup_config(
    _admin: AdminOnly,
    db: Session = Depends(get_db),
):
    cfg = backup_service.get_or_create_config(db)
    return _to_config_response(cfg)


@router.put("/config", response_model=BackupConfigResponse)
def update_backup_config(
    body: BackupConfigUpdate,
    _admin: AdminOnly,
    db: Session = Depends(get_db),
):
    cfg = backup_service.update_config(db, body)
    scheduler_service.reload_backup_job()
    return _to_config_response(cfg)


@router.get("/status", response_model=BackupStatusResponse)
def get_backup_status(
    _admin: AdminOnly,
    db: Session = Depends(get_db),
):
    last_log = backup_service.get_last_log(db)
    return BackupStatusResponse(
        is_running=backup_service.is_backup_running(),
        last_log=BackupLogResponse.model_validate(last_log) if last_log else None,
        next_run_at=scheduler_service.get_next_run_time(),
    )


@router.post("/run", response_model=BackupRunResponse)
async def trigger_manual_backup(
    _admin: AdminOnly,
):
    if backup_service.is_backup_running():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya hay una tarea de backup en ejecución.",
        )

    try:
        log = await backup_service.execute_backup(trigger_type="manual")
        if log.status == "success":
            return BackupRunResponse(
                success=True,
                message=f"Backup {log.file_name} generado y subido a S3 con éxito.",
                log=BackupLogResponse.model_validate(log),
            )
        else:
            return BackupRunResponse(
                success=False,
                message=f"El backup falló: {log.error_message}",
                log=BackupLogResponse.model_validate(log),
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado al ejecutar backup: {str(e)}",
        )


@router.get("/logs", response_model=list[BackupLogResponse])
def get_backup_logs(
    _admin: AdminOnly,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    logs = backup_service.list_logs(db, limit=limit)
    return [BackupLogResponse.model_validate(log) for log in logs]
