import logging
import math
import secrets
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.rate_limit import rate_limit
from app.core.security import decode_access_token
from app.db.models.job import CrawlState, JobPosting, JobSkill, JobSource
from app.db.models.skill import Skill
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.job import (
    CrawlTriggerRequest,
    CrawlTriggerResponse,
    JobPostingRead,
    JobPostingsPage,
    JobSourceRead,
    TopSkillsResponse,
)
from app.services.crawl.runner import run_crawl_pipeline
from app.services.jobs.demand import get_top_demanded_skills
from app.services.llm import get_llm_provider
from app.services.sources.budget import (
    get_daily_usage,
    get_remaining_budget,
)
from app.services.sources.registry import source_registry

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Jobs & Sources"])


async def verify_crawl_auth(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_crawl_token: Annotated[str | None, Header(alias="X-Crawl-Token")] = None,
) -> bool:
    """Verify crawler caller via X-Crawl-Token or admin JWT."""
    configured_token = settings.CRAWL_TRIGGER_TOKEN
    if (
        configured_token
        and x_crawl_token
        and secrets.compare_digest(x_crawl_token.strip(), configured_token.strip())
    ):
        return True

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        try:
            payload = decode_access_token(token)
            user_id_str = payload.get("sub")
            if user_id_str:
                user_id = uuid.UUID(user_id_str)
                user_res = await db.execute(select(User).where(User.id == user_id))
                user = user_res.scalar_one_or_none()
                if user and user.role == "admin":
                    return True
        except Exception:
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized: valid X-Crawl-Token header or admin credentials required",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post(
    "/jobs/crawl",
    response_model=CrawlTriggerResponse,
    dependencies=[Depends(rate_limit(times=10, seconds=60, name="job_crawl"))],
)
async def trigger_crawl(
    db: Annotated[AsyncSession, Depends(get_db)],
    _auth: Annotated[bool, Depends(verify_crawl_auth)],
    body: CrawlTriggerRequest | None = None,
) -> CrawlTriggerResponse:
    """Trigger an incremental crawl across enabled sources by priority."""
    pairs = None
    if body and body.pairs:
        pairs = [(p.role, p.location) for p in body.pairs]
    sources = body.sources if body else None
    extract_skills = body.extract_skills if body else True

    llm = None
    if extract_skills:
        try:
            llm = get_llm_provider()
        except Exception:
            logger.warning("Could not initialize default LLM provider for crawl")

    return await run_crawl_pipeline(
        db=db,
        pairs=pairs,
        sources=sources,
        extract_skills=extract_skills,
        llm_provider=llm,
    )


@router.get("/jobs/skills/top", response_model=TopSkillsResponse)
async def top_skills_demand(
    db: Annotated[AsyncSession, Depends(get_db)],
    role: Annotated[str, Query(min_length=1, description="Target role query")],
    location: Annotated[str | None, Query(description="Location filter")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    days: Annotated[int, Query(ge=1, le=90, description="Trend window in days")] = 30,
) -> TopSkillsResponse:
    """Retrieve top demanded skills for a given role and location with 30-day trend."""
    return await get_top_demanded_skills(
        db=db,
        role_query=role,
        location=location,
        limit=limit,
        trend_days=days,
    )


@router.get("/jobs", response_model=JobPostingsPage)
async def list_jobs(
    db: Annotated[AsyncSession, Depends(get_db)],
    role: str | None = None,
    location: str | None = None,
    source: str | None = None,
    skill: str | None = None,
    active_only: bool = True,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> JobPostingsPage:
    """List persisted job postings with role, location, source, and skill filters."""
    query = select(JobPosting).options(
        selectinload(JobPosting.skills).selectinload(JobSkill.skill)
    )

    if active_only:
        query = query.where(JobPosting.is_expired.is_(False))

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
                is_expired=p.is_expired,
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
        inst = source_registry.get_source(src.name)
        daily_budget = inst.default_daily_budget if inst else 50

        used = await get_daily_usage(db, src.name)
        remaining = await get_remaining_budget(db, src.name, limit=daily_budget)

        state_stmt = select(func.max(CrawlState.last_run_at)).where(
            CrawlState.source == src.name
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
