import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.job import JobSource

logger = logging.getLogger(__name__)

INITIAL_JOB_SOURCES: list[dict[str, object]] = [
    {
        "name": "adzuna",
        "priority": 1,
        "enabled": True,
        "attribution_text": "Powered by Adzuna",
        "attribution_url": "https://www.adzuna.com",
        "may_display_listing": True,
    },
    {
        "name": "jooble",
        "priority": 1,
        "enabled": True,
        "attribution_text": "Jobs via Jooble",
        "attribution_url": "https://jooble.org",
        "may_display_listing": True,
    },
    {
        "name": "remotive",
        "priority": 2,
        "enabled": True,
        "attribution_text": "Data from Remotive",
        "attribution_url": "https://remotive.com",
        "may_display_listing": False,  # Terms: internal skill stats only
    },
    {
        "name": "remoteok",
        "priority": 2,
        "enabled": True,
        "attribution_text": "Jobs by RemoteOK",
        "attribution_url": "https://remoteok.com",
        "may_display_listing": True,
    },
    {
        "name": "wwr_rss",
        "priority": 2,
        "enabled": True,
        "attribution_text": "Jobs via We Work Remotely",
        "attribution_url": "https://weworkremotely.com",
        "may_display_listing": True,
    },
    {
        "name": "arbeitnow",
        "priority": 3,
        "enabled": False,  # Disabled by default
        "attribution_text": "Jobs by Arbeitnow",
        "attribution_url": "https://www.arbeitnow.com",
        "may_display_listing": True,
    },
    {
        "name": "hn_hiring",
        "priority": 3,
        "enabled": False,  # Disabled by default
        "attribution_text": "Hacker News Who is Hiring",
        "attribution_url": "https://news.ycombinator.com",
        "may_display_listing": True,
    },
    {
        "name": "fixture",
        "priority": 10,
        "enabled": True,
        "attribution_text": "Curated sample dataset",
        "attribution_url": None,
        "may_display_listing": True,
    },
]


async def seed_job_sources(db: AsyncSession) -> int:
    """Ensure standard job sources exist in DB with their priority and terms."""
    created_count = 0
    for meta in INITIAL_JOB_SOURCES:
        name = str(meta["name"])
        query = select(JobSource).where(JobSource.name == name)
        res = await db.execute(query)
        existing = res.scalar_one_or_none()

        if existing is None:
            attr_text = (
                str(meta["attribution_text"]) if meta["attribution_text"] else None
            )
            attr_url = str(meta["attribution_url"]) if meta["attribution_url"] else None
            source = JobSource(
                name=name,
                priority=int(str(meta["priority"])),
                enabled=bool(meta["enabled"]),
                attribution_text=attr_text,
                attribution_url=attr_url,
                may_display_listing=bool(meta["may_display_listing"]),
            )
            db.add(source)
            created_count += 1

    if created_count > 0:
        await db.commit()
        logger.info(f"Seeded {created_count} initial job sources into database")

    return created_count
