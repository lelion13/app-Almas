from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BackupConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    schedule_type: str = Field(default="daily", description="daily or weekly")
    schedule_time: str = Field(default="03:00", description="HH:MM in 24h format")
    schedule_day_of_week: int | None = Field(default=None, description="0=Monday .. 6=Sunday or similar")
    s3_endpoint_url: str | None = Field(default=None, description="Custom S3 endpoint URL (e.g. for Cloudflare R2)")
    s3_bucket_name: str = Field(default="", description="S3 bucket name")
    s3_region_name: str = Field(default="auto", description="S3 region name")
    s3_access_key_id: str = Field(default="", description="S3 access key ID")
    s3_secret_access_key: str | None = Field(default=None, description="S3 secret access key. Leave empty/null to keep existing")
    s3_prefix: str = Field(default="almas-backups/", description="S3 key prefix path")
    retention_count: int = Field(default=15, ge=1, le=365, description="Number of backups to retain in S3")


class BackupConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enabled: bool
    schedule_type: str
    schedule_time: str
    schedule_day_of_week: int | None
    s3_endpoint_url: str | None
    s3_bucket_name: str
    s3_region_name: str
    s3_access_key_id: str
    has_secret_access_key: bool
    s3_prefix: str
    retention_count: int
    updated_at: datetime | None


class BackupLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trigger_type: str
    status: str
    file_name: str
    file_size_bytes: int | None
    storage_key: str | None
    duration_seconds: float | None
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None


class BackupRunResponse(BaseModel):
    success: bool
    message: str
    log: BackupLogResponse | None = None


class BackupStatusResponse(BaseModel):
    is_running: bool
    last_log: BackupLogResponse | None = None
    next_run_at: datetime | None = None
