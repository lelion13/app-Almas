import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SystemBackupConfig(Base):
    __tablename__ = "system_backup_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    schedule_type: Mapped[str] = mapped_column(String(32), nullable=False, default="daily")
    schedule_time: Mapped[str] = mapped_column(String(8), nullable=False, default="03:00")
    schedule_day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    s3_endpoint_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    s3_bucket_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    s3_region_name: Mapped[str] = mapped_column(String(64), nullable=False, default="auto")
    s3_access_key_id: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    s3_secret_access_key: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    s3_prefix: Mapped[str] = mapped_column(String(255), nullable=False, default="almas-backups/")
    retention_count: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SystemBackupLog(Base):
    __tablename__ = "system_backup_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False)  # manual | scheduled
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # running | success | failed
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
