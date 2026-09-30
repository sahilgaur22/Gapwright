import math
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.job import CrawlState, JobPosting, JobSkill, JobSource
from app.db.models.skill import Skill
from app.db.session import get_db
from app.schemas.job import JobPostingRead, JobPostingsPage, JobSourceRead
from app.services.sources.budget import (
    get_daily_usage,
    get_remaining_budget,
)
from app.services.sources.registry import source_registry

router = APIRouter(tags=["Jobs & Sources"])


@router.get("/jobs", response_model=JobPostingsPage)
async def list_jobs(
    db: Annotated[AsyncSession, Depends(get_db)],
    role: str | None = None,
    location: str | None = None,
    source: str | None = None,
    skill: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> JobPostingsPage:
    """List persisted job postings with role, location, source, and skill filters."""
    query = select(JobPosting).options(
        selectinload(JobPosting.skills).selectinload(JobSkill.skill)
    )

    if role:
        r = f"%{role.strip().lower()}%"
        query = query.where(
            func.lower(JobPosting.title).like(r)
            | func.lower(JobPosting.description).like(r)
        )

    if location:
        loc = f"%{location.strip().lower()}%"
        query = query.where(func.lower(JobPosting.location).like(loc))

    if source:
        query = query.where(JobPosting.source == source.strip().lower())

    if skill:
        skill_clean = skill.strip().lower()
        query = (
            query.join(JobPosting.skills)
            .join(JobSkill.skill)
            .where(func.lower(Skill.canonical_name) == skill_clean)
        )

    # Count total
    count_subq = query.with_only_columns(func.count(JobPosting.id.distinct()))
    total_res = await db.execute(count_subq)
    total = total_res.scalar() or 0

    # Order and paginate
    query = (
        query.order_by(JobPosting.posted_at.desc().nulls_last())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    res = await db.execute(query)
    postings = list(res.scalars().all())

    items: list[JobPostingRead] = []
    for p in postings:
        skill_names = [js.skill.canonical_name for js in p.skills if js.skill]
        items.append(
            JobPostingRead(
                id=p.id,
                source=p.source,
                external_id=p.external_id,
                title=p.title,
                company=p.company,
                location=p.location,
                description=p.description,
                description_is_truncated=p.description_is_truncated,
                url=p.url,
                posted_at=p.posted_at,
                scraped_at=p.scraped_at,
                last_seen_at=p.last_seen_at,
                skills=skill_names,
            )
        )

    pages = math.ceil(total / page_size) if total > 0 else 0

    return JobPostingsPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/sources", response_model=list[JobSourceRead])
async def list_sources(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[JobSourceRead]:
    """List registered sources with remaining daily quotas and crawl status."""
    db_sources_res = await db.execute(
        select(JobSource).order_by(JobSource.priority, JobSource.name)
    )
    db_sources = list(db_sources_res.scalars().all())

    results: list[JobSourceRead] = []

    for src in db_sources:
        # Get connector instance if registered
        inst = source_registry.get_source(src.name)
        daily_budget = inst.default_daily_budget if inst else 50

        used = await get_daily_usage(db, src.name)
        remaining = await get_remaining_budget(
            db, src.name, limit=daily_budget
        )

        # Query latest crawl timestamp for this source
        state_stmt = (
            select(func.max(CrawlState.last_run_at))
            .where(CrawlState.source == src.name)
        )
        state_res = await db.execute(state_stmt)
        last_run = state_res.scalar()

        results.append(
            JobSourceRead(
                name=src.name,
                priority=src.priority,
                enabled=src.enabled,
                attribution_text=src.attribution_text,
                attribution_url=src.attribution_url,
                may_display_listing=src.may_display_listing,
                daily_budget=daily_budget,
                daily_calls_used=used,
                remaining_budget=remaining,
                last_run_at=last_run,
            )
        )

    return results
