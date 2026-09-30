import logging
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.job import JobPosting, JobSkill, SkillDemandDaily
from app.db.models.skill import Skill
from app.schemas.job import SkillDemandItem, TopSkillsResponse

logger = logging.getLogger(__name__)


def parse_crawl_pairs(raw: str | None = None) -> list[tuple[str, str]]:
    """Parse configured role|location pairs from semicolon-separated string."""
    pairs_str = raw if raw is not None else settings.CRAWL_PAIRS
    if not pairs_str:
        return []

    result: list[tuple[str, str]] = []
    for chunk in pairs_str.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = chunk.split("|", 1)
        role = parts[0].strip()
        loc = parts[1].strip() if len(parts) > 1 else ""
        if role:
            result.append((role, loc))
    return result


async def generate_demand_daily_snapshot(
    db: AsyncSession,
    target_date: date | None = None,
    pairs: list[tuple[str, str]] | None = None,
    window_days: int = settings.ANALYSIS_WINDOW_DAYS,
) -> int:
    """Snapshot skill demand metrics per role and location for a given date."""
    snap_day = target_date or datetime.now(UTC).date()
    cutoff = datetime.now(UTC) - timedelta(days=window_days)

    crawl_pairs = pairs if pairs is not None else parse_crawl_pairs()
    if not crawl_pairs:
        # Default fallback
        crawl_pairs = [("Software Engineer", "")]

    records_count = 0

    for role, loc in crawl_pairs:
        norm_role = role.strip().lower()
        norm_loc = loc.strip().lower()

        # Build base filter for active postings in window
        filters = [
            JobPosting.is_expired.is_(False),
            JobPosting.last_seen_at >= cutoff,
            func.lower(JobPosting.title).like(f"%{norm_role}%"),
        ]
        if norm_loc and norm_loc != "remote":
            filters.append(func.lower(JobPosting.location).like(f"%{norm_loc}%"))

        total_stmt = select(func.count(JobPosting.id)).where(*filters)
        total_res = await db.execute(total_stmt)
        total_postings = total_res.scalar_one() or 0

        if total_postings == 0:
            continue

        # Count skills across matching postings
        skill_counts_stmt = (
            select(
                JobSkill.skill_id,
                func.count(JobSkill.job_id).label("cnt"),
            )
            .join(JobPosting, JobPosting.id == JobSkill.job_id)
            .where(*filters)
            .group_by(JobSkill.skill_id)
        )
        skill_res = await db.execute(skill_counts_stmt)
        skill_rows = skill_res.all()

        for skill_id, count in skill_rows:
            demand_pct = round(count / total_postings, 4)

            # Check if record already exists for (day, role, loc, skill_id)
            existing_stmt = select(SkillDemandDaily).where(
                SkillDemandDaily.day == snap_day,
                SkillDemandDaily.role_query == role,
                SkillDemandDaily.location == loc,
                SkillDemandDaily.skill_id == skill_id,
            )
            existing_res = await db.execute(existing_stmt)
            existing = existing_res.scalar_one_or_none()

            if existing is not None:
                existing.postings_count = count
                existing.demand_pct = demand_pct
            else:
                snapshot = SkillDemandDaily(
                    day=snap_day,
                    role_query=role,
                    location=loc,
                    skill_id=skill_id,
                    postings_count=count,
                    demand_pct=demand_pct,
                )
                db.add(snapshot)
            records_count += 1

    await db.commit()
    logger.info("Generated %d skill demand snapshot records", records_count)
    return records_count


async def get_top_demanded_skills(
    db: AsyncSession,
    role_query: str,
    location: str | None = None,
    limit: int = 20,
    trend_days: int = 30,
    window_days: int = settings.ANALYSIS_WINDOW_DAYS,
) -> TopSkillsResponse:
    """Retrieve top demanded skills for a given role and location with 30-day trend."""
    norm_role = role_query.strip().lower()
    norm_loc = (location or "").strip().lower()
    cutoff = datetime.now(UTC) - timedelta(days=window_days)

    filters = [
        JobPosting.is_expired.is_(False),
        JobPosting.last_seen_at >= cutoff,
        func.lower(JobPosting.title).like(f"%{norm_role}%"),
    ]
    if norm_loc and norm_loc != "remote":
        filters.append(func.lower(JobPosting.location).like(f"%{norm_loc}%"))

    # Total matching postings
    total_stmt = select(func.count(JobPosting.id)).where(*filters)
    total_res = await db.execute(total_stmt)
    total_postings = total_res.scalar_one() or 0

    if total_postings == 0:
        return TopSkillsResponse(
            role_query=role_query,
            location=location,
            total_postings=0,
            analysis_window_days=window_days,
            trend_window_days=trend_days,
            skills=[],
        )

    # Top skills with counts
    top_stmt = (
        select(
            Skill.id,
            Skill.canonical_name,
            Skill.category,
            func.count(JobSkill.job_id).label("skill_cnt"),
        )
        .join(JobSkill, Skill.id == JobSkill.skill_id)
        .join(JobPosting, JobPosting.id == JobSkill.job_id)
        .where(*filters)
        .group_by(Skill.id, Skill.canonical_name, Skill.category)
        .order_by(func.count(JobSkill.job_id).desc(), Skill.canonical_name.asc())
        .limit(limit)
    )
    top_res = await db.execute(top_stmt)
    top_rows = top_res.all()

    # Pre-fetch historical snapshots for trend calculation over trend_days
    trend_cutoff = datetime.now(UTC).date() - timedelta(days=trend_days)
    skill_ids = [row[0] for row in top_rows]

    trend_stmt = (
        select(
            SkillDemandDaily.skill_id,
            SkillDemandDaily.day,
            SkillDemandDaily.demand_pct,
        )
        .where(
            SkillDemandDaily.skill_id.in_(skill_ids),
            SkillDemandDaily.day >= trend_cutoff,
            func.lower(SkillDemandDaily.role_query).like(f"%{norm_role}%"),
        )
        .order_by(SkillDemandDaily.skill_id, SkillDemandDaily.day.asc())
    )
    trend_res = await db.execute(trend_stmt)
    trend_rows = trend_res.all()

    # Group trend points by skill_id
    history_by_skill: dict[uuid.UUID, list[tuple[date, float]]] = {}
    for sid, sday, dpct in trend_rows:
        history_by_skill.setdefault(sid, []).append((sday, dpct))

    items: list[SkillDemandItem] = []
    for skill_id, canonical_name, category, count in top_rows:
        demand_pct = round(count / total_postings, 4)

        # Compute trend percentage
        trend_pts = history_by_skill.get(skill_id, [])
        trend_pct = 0.0
        if len(trend_pts) >= 2:
            earliest_pct = trend_pts[0][1]
            latest_pct = trend_pts[-1][1]
            trend_pct = round(latest_pct - earliest_pct, 4)
        elif len(trend_pts) == 1:
            # Compared to current live demand
            trend_pct = round(demand_pct - trend_pts[0][1], 4)

        items.append(
            SkillDemandItem(
                skill_id=skill_id,
                name=canonical_name,
                category=category,
                postings_count=count,
                demand_pct=demand_pct,
                trend_pct=trend_pct,
            )
        )

    return TopSkillsResponse(
        role_query=role_query,
        location=location,
        total_postings=total_postings,
        analysis_window_days=window_days,
        trend_window_days=trend_days,
        skills=items,
    )
