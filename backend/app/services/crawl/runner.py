import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.job import JobPosting, JobSource
from app.schemas.job import CrawlTriggerResponse
from app.services.crawl.state import get_crawl_state, update_crawl_state
from app.services.jobs.demand import generate_demand_daily_snapshot, parse_crawl_pairs
from app.services.jobs.persistence import persist_raw_jobs
from app.services.llm.base import LLMProvider
from app.services.sources.budget import get_remaining_budget, record_usage
from app.services.sources.registry import source_registry

logger = logging.getLogger(__name__)


async def expire_stale_postings(
    db: AsyncSession,
    days: int = settings.ANALYSIS_WINDOW_DAYS,
) -> int:
    """Mark job postings not seen within the rolling analysis window as expired."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    stmt = select(JobPosting).where(
        JobPosting.last_seen_at < cutoff,
        JobPosting.is_expired.is_(False),
    )
    result = await db.execute(stmt)
    stale_postings = result.scalars().all()

    count = 0
    for posting in stale_postings:
        posting.is_expired = True
        count += 1

    if count > 0:
        await db.commit()
        logger.info("Marked %d stale job postings as expired", count)
    return count


async def run_crawl_pipeline(
    db: AsyncSession,
    *,
    pairs: list[tuple[str, str]] | None = None,
    sources: list[str] | None = None,
    extract_skills: bool = True,
    llm_provider: LLMProvider | None = None,
) -> CrawlTriggerResponse:
    """Execute scheduled or on-demand crawl across enabled sources by priority."""
    crawl_pairs = pairs if pairs is not None else parse_crawl_pairs()
    if not crawl_pairs:
        crawl_pairs = [("Software Engineer", "")]

    # Fetch enabled sources ordered by priority
    source_stmt = (
        select(JobSource)
        .where(JobSource.enabled.is_(True))
        .order_by(JobSource.priority.asc())
    )
    source_res = await db.execute(source_stmt)
    db_sources = source_res.scalars().all()

    if sources:
        source_names_filter = {s.lower().strip() for s in sources}
        db_sources = [s for s in db_sources if s.name.lower() in source_names_filter]

    total_persisted = 0
    sources_crawled_count = 0

    for source_model in db_sources:
        source_impl = source_registry.get_source(source_model.name)
        if source_impl is None:
            logger.debug(
                "Source %s not registered in registry, skipping",
                source_model.name,
            )
            continue

        # Check daily budget
        budget_limit = getattr(
            settings, f"{source_model.name.upper()}_DAILY_BUDGET", 50
        )
        remaining = await get_remaining_budget(
            db, source_model.name, limit=budget_limit
        )
        if remaining <= 0:
            logger.warning(
                "Source %s budget exhausted for today (%d remaining). Skipping crawl.",
                source_model.name,
                remaining,
            )
            continue

        sources_crawled_count += 1

        for role, loc in crawl_pairs:
            try:
                # Check crawl state for incremental fetch
                state = await get_crawl_state(db, source_model.name, role, loc)
                since = state.newest_posted_at if state else None

                raw_jobs = await source_impl.search(
                    role=role,
                    location=loc,
                    since=since,
                    limit=20,
                )
                await record_usage(db, source_model.name, calls=1)

                if raw_jobs:
                    persist_res = await persist_raw_jobs(
                        db=db,
                        raw_jobs=raw_jobs,
                        extract_skills=extract_skills,
                        llm_provider=llm_provider,
                    )
                    total_persisted += (
                        persist_res.created_count + persist_res.updated_count
                    )

                    newest_posted = max(
                        (
                            job.posted_at
                            for job in raw_jobs
                            if job.posted_at is not None
                        ),
                        default=None,
                    )
                    await update_crawl_state(
                        db=db,
                        source=source_model.name,
                        role_query=role,
                        location=loc,
                        newest_posted_at=newest_posted,
                    )
                else:
                    await update_crawl_state(
                        db=db,
                        source=source_model.name,
                        role_query=role,
                        location=loc,
                    )

            except Exception as e:
                logger.error(
                    "Error crawling %s for %s in %s: %s",
                    source_model.name,
                    role,
                    loc,
                    str(e),
                )
                await update_crawl_state(
                    db=db,
                    source=source_model.name,
                    role_query=role,
                    location=loc,
                )

    # Expire stale postings
    expired_count = await expire_stale_postings(db, days=settings.ANALYSIS_WINDOW_DAYS)

    # Generate daily snapshot
    snapshot_count = await generate_demand_daily_snapshot(
        db,
        pairs=crawl_pairs,
        window_days=settings.ANALYSIS_WINDOW_DAYS,
    )

    return CrawlTriggerResponse(
        status="completed",
        pairs_processed=len(crawl_pairs),
        sources_crawled=sources_crawled_count,
        jobs_persisted=total_persisted,
        expired_count=expired_count,
        snapshot_records_created=snapshot_count,
    )
