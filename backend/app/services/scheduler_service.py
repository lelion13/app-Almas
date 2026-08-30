import asyncio
from datetime import datetime
import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.backup_service import execute_backup, get_or_create_config

logger = logging.getLogger(__name__)

JOB_ID = "system_database_backup"
_scheduler: AsyncIOScheduler | None = None


async def _scheduled_backup_wrapper():
    logger.info("Executing scheduled database backup...")
    try:
        log = await execute_backup(trigger_type="scheduled")
        if log.status == "success":
            logger.info("Scheduled backup succeeded: %s", log.file_name)
        else:
            logger.error("Scheduled backup failed: %s", log.error_message)
    except Exception as e:
        logger.error("Error running scheduled backup job: %s", e, exc_info=True)


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


def get_next_run_time() -> datetime | None:
    scheduler = get_scheduler()
    job = scheduler.get_job(JOB_ID)
    if job and job.next_run_time:
        return job.next_run_time
    return None


def reload_backup_job():
    scheduler = get_scheduler()
    db = SessionLocal()
    try:
        config = get_or_create_config(db)
        if not config.enabled:
            if scheduler.get_job(JOB_ID):
                scheduler.remove_job(JOB_ID)
                logger.info("Removed scheduled backup job (backups disabled).")
            return

        time_parts = config.schedule_time.split(":")
        hour = int(time_parts[0]) if len(time_parts) > 0 else 3
        minute = int(time_parts[1]) if len(time_parts) > 1 else 0

        tz = ZoneInfo(settings.timezone_local)

        if config.schedule_type == "weekly":
            dow = config.schedule_day_of_week if config.schedule_day_of_week is not None else 0
            trigger = CronTrigger(day_of_week=dow, hour=hour, minute=minute, timezone=tz)
        else:
            trigger = CronTrigger(hour=hour, minute=minute, timezone=tz)

        scheduler.add_job(
            _scheduled_backup_wrapper,
            trigger=trigger,
            id=JOB_ID,
            name="Scheduled Database Backup",
            replace_existing=True,
        )
        logger.info(
            "Scheduled backup job configured (%s at %02d:%02d %s). Next run: %s",
            config.schedule_type,
            hour,
            minute,
            settings.timezone_local,
            get_next_run_time(),
        )
    except Exception as e:
        logger.error("Failed to reload backup scheduler job: %s", e, exc_info=True)
    finally:
        db.close()


def start_scheduler():
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("Backup AsyncIOScheduler started.")
    reload_backup_job()


def shutdown_scheduler():
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Backup AsyncIOScheduler shutdown.")
