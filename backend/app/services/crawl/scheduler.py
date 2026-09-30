import logging
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.services.crawl.runner import run_crawl_pipeline

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def scheduled_crawl_job() -> None:
    """Scheduled task to run crawl pipeline in the background."""
    logger.info("Executing scheduled crawl pipeline task...")
    try:
        async with AsyncSessionLocal() as session:
            result = await run_crawl_pipeline(session)
            logger.info("Scheduled crawl task completed: %s", result.model_dump())
    except Exception as e:
        logger.error("Scheduled crawl task failed: %s", str(e), exc_info=True)


def start_local_scheduler() -> AsyncIOScheduler | None:
    """Initialize and start in-process APScheduler if enabled in configuration."""
    global _scheduler
    if not settings.ENABLE_LOCAL_SCHEDULER:
        logger.debug("Local APScheduler disabled via ENABLE_LOCAL_SCHEDULER=false")
        return None

    if _scheduler is not None and _scheduler.running:
        return _scheduler

    scheduler = AsyncIOScheduler()
    # Run crawl every 6 hours by default
    scheduler.add_job(
        scheduled_crawl_job,
        trigger="interval",
        hours=6,
        id="scheduled_crawl_pipeline",
        name="Scheduled Job Crawl and Demand Snapshot",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("Local APScheduler started with 6-hour crawl interval")
    return _scheduler


def stop_local_scheduler(scheduler: Any = None) -> None:
    """Gracefully shut down the background scheduler."""
    global _scheduler
    sched = scheduler or _scheduler
    if sched is not None and sched.running:
        sched.shutdown(wait=False)
        logger.info("Local APScheduler stopped")
    _scheduler = None
