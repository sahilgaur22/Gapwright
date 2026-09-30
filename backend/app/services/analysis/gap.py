import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.models.analysis import Analysis, AnalysisItem
from app.db.models.job import JobPosting, JobSkill
from app.db.models.skill import Skill
from app.db.models.syllabus import Syllabus, SyllabusSkill
from app.services.analysis.matcher import match_all_skills

logger = logging.getLogger(__name__)


async def compute_gap_analysis(
    db: AsyncSession,
    syllabus_id: uuid.UUID,
    role_query: str,
    location: str | None = None,
    remote_only: bool = False,
    window_days: int = settings.ANALYSIS_WINDOW_DAYS,
    obsolete_threshold: float = settings.OBSOLETE_DEMAND_THRESHOLD,
    match_threshold: float = settings.SKILL_MATCH_THRESHOLD,
) -> Analysis:
    """Compute curriculum gap percentage, coverage, and skill classifications."""
    # 1. Load syllabus and its associated skills
    s_stmt = (
        select(Syllabus)
        .options(selectinload(Syllabus.skills).selectinload(SyllabusSkill.skill))
        .where(Syllabus.id == syllabus_id)
    )
    s_res = await db.execute(s_stmt)
    syllabus = s_res.scalar_one_or_none()
    if syllabus is None:
        raise ValueError(f"Syllabus with ID '{syllabus_id}' not found")

    syllabus_skills: list[Skill] = [
        assoc.skill for assoc in syllabus.skills if assoc.skill is not None
    ]

    # 2. Query active job postings matching criteria within rolling window
    cutoff = datetime.now(UTC) - timedelta(days=window_days)
    norm_role = role_query.strip().lower()

    postings_query = select(JobPosting).where(
        JobPosting.is_expired.is_(False),
        JobPosting.last_seen_at >= cutoff,
        func.lower(JobPosting.title).like(f"%{norm_role}%"),
    )

    location_tag = "all"
    if remote_only or (location and location.strip().lower() == "remote"):
        # Remote market uses P2 sources and remote postings
        location_tag = "remote"
        postings_query = postings_query.where(
            JobPosting.source.in_(["remotive", "remoteok", "wwr_rss", "fixture"])
            | func.lower(JobPosting.location).like("%remote%")
        )
    elif location and location.strip():
        # Location-specific analysis uses P1 sources (Adzuna, Jooble, Fixture)
        location_tag = location.strip()
        norm_loc = location_tag.lower()
        postings_query = postings_query.where(
            JobPosting.source.in_(["adzuna", "jooble", "fixture"]),
            func.lower(JobPosting.location).like(f"%{norm_loc}%"),
        )

    matching_postings_res = await db.execute(postings_query)
    matching_postings = list(matching_postings_res.scalars().all())
    total_postings = len(matching_postings)

    # 3. Calculate market skills and their demand percentages
    market_skill_records: list[tuple[Skill, int, float]] = []
    market_skills_list: list[Skill] = []

    if total_postings > 0:
        posting_ids = [p.id for p in matching_postings]
        market_stmt = (
            select(Skill, func.count(JobSkill.job_id.distinct()).label("cnt"))
            .join(JobSkill, Skill.id == JobSkill.skill_id)
            .where(JobSkill.job_id.in_(posting_ids))
            .group_by(Skill.id)
            .order_by(func.count(JobSkill.job_id.distinct()).desc())
        )
        market_res = await db.execute(market_stmt)
        for skill_model, count in market_res.all():
            demand_pct = round(count / total_postings, 4)
            market_skill_records.append((skill_model, count, demand_pct))
            market_skills_list.append(skill_model)

    # 4. Perform tiered semantic matching between syllabus and market skills
    matches = match_all_skills(
        syllabus_skills=syllabus_skills,
        market_skills=market_skills_list,
        threshold=match_threshold,
    )

    # Maps for fast lookup
    matched_market_skill_ids = {m.market_skill_id: m for m in matches}
    matched_syllabus_skill_ids = {m.syllabus_skill_id: m for m in matches}

    # 5. Compute coverage and gap percentages per formula in Section 4:
    # coverage = sum(weight(skills in both)) / sum(weight(all market skills))
    total_market_weight = sum(record[2] for record in market_skill_records)
    covered_market_weight = sum(
        record[2]
        for record in market_skill_records
        if record[0].id in matched_market_skill_ids
    )

    if total_market_weight > 0.0:
        coverage_ratio = covered_market_weight / total_market_weight
        coverage_pct = round(min(100.0, coverage_ratio * 100.0), 2)
    else:
        coverage_pct = 0.0

    gap_pct = round(100.0 - coverage_pct, 2)

    # 6. Classify items into covered, missing, and obsolete
    items_to_persist: list[AnalysisItem] = []

    # Covered items (market skills matched by syllabus)
    covered_candidates = [
        rec for rec in market_skill_records if rec[0].id in matched_market_skill_ids
    ]
    covered_candidates.sort(key=lambda r: (r[2], r[1]), reverse=True)
    for rank, (skill_m, cnt, dpct) in enumerate(covered_candidates, start=1):
        items_to_persist.append(
            AnalysisItem(
                skill_id=skill_m.id,
                kind="covered",
                demand_count=cnt,
                demand_pct=dpct,
                rank=rank,
            )
        )

    # Missing items (market skills NOT covered by syllabus)
    missing_candidates = [
        rec for rec in market_skill_records if rec[0].id not in matched_market_skill_ids
    ]
    missing_candidates.sort(key=lambda r: (r[2], r[1]), reverse=True)
    for rank, (skill_m, cnt, dpct) in enumerate(missing_candidates, start=1):
        items_to_persist.append(
            AnalysisItem(
                skill_id=skill_m.id,
                kind="missing",
                demand_count=cnt,
                demand_pct=dpct,
                rank=rank,
            )
        )

    # Obsolete items (syllabus skills with demand below obsolete_threshold)
    # Market demand map for quick lookup
    market_demand_map = {rec[0].id: rec for rec in market_skill_records}

    obsolete_candidates: list[tuple[Skill, int, float]] = []
    for s_skill in syllabus_skills:
        match_info = matched_syllabus_skill_ids.get(s_skill.id)
        if match_info is None:
            # Not in market at all -> demand 0
            obsolete_candidates.append((s_skill, 0, 0.0))
        else:
            market_rec = market_demand_map.get(match_info.market_skill_id)
            if market_rec is None or market_rec[2] < obsolete_threshold:
                m_cnt = market_rec[1] if market_rec else 0
                m_dpct = market_rec[2] if market_rec else 0.0
                obsolete_candidates.append((s_skill, m_cnt, m_dpct))

    obsolete_candidates.sort(key=lambda r: (r[2], r[1]))
    for rank, (s_skill, cnt, dpct) in enumerate(obsolete_candidates, start=1):
        items_to_persist.append(
            AnalysisItem(
                skill_id=s_skill.id,
                kind="obsolete",
                demand_count=cnt,
                demand_pct=dpct,
                rank=rank,
            )
        )

    # 7. Persist analysis record
    analysis = Analysis(
        id=uuid.uuid4(),
        syllabus_id=syllabus_id,
        role_query=role_query,
        location=location_tag,
        gap_pct=gap_pct,
        coverage_pct=coverage_pct,
    )
    db.add(analysis)
    await db.flush()

    for item in items_to_persist:
        item.analysis_id = analysis.id
        db.add(item)

    await db.commit()

    # Re-fetch analysis with relationships loaded
    fetch_stmt = (
        select(Analysis)
        .options(
            selectinload(Analysis.items).selectinload(AnalysisItem.skill),
        )
        .where(Analysis.id == analysis.id)
    )
    fetch_res = await db.execute(fetch_stmt)
    persisted_analysis = fetch_res.scalar_one()

    logger.info(
        "Analysis %s complete: coverage=%.2f%%, gap=%.2f%% "
        "(%d covered, %d missing, %d obsolete)",
        analysis.id,
        coverage_pct,
        gap_pct,
        len(covered_candidates),
        len(missing_candidates),
        len(obsolete_candidates),
    )
    return persisted_analysis
