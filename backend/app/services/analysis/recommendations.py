import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.analysis import Analysis, AnalysisItem
from app.db.models.job import SkillDemandDaily
from app.schemas.analysis import (
    CurriculumRecommendationsResponse,
    SkillRecommendationAction,
    SkillRecommendationItem,
)
from app.services.llm.base import LLMProvider
from app.services.llm.prompts import (
    RECOMMENDATIONS_USER_TEMPLATE,
    SYSTEM_INSTRUCTION_RECOMMENDATIONS,
)

logger = logging.getLogger(__name__)


async def generate_curriculum_recommendations(
    db: AsyncSession,
    analysis_id: uuid.UUID,
    llm_provider: LLMProvider | None = None,
    max_add: int = 5,
    max_drop: int = 5,
    trend_days: int = 30,
) -> CurriculumRecommendationsResponse:
    """Generate grounded curriculum addition and drop recommendations."""
    # 1. Fetch analysis with items, skills, and syllabus
    stmt = (
        select(Analysis)
        .options(
            selectinload(Analysis.items).selectinload(AnalysisItem.skill),
            selectinload(Analysis.syllabus),
        )
        .where(Analysis.id == analysis_id)
    )
    res = await db.execute(stmt)
    analysis = res.scalar_one_or_none()
    if analysis is None:
        raise ValueError(f"Analysis with ID '{analysis_id}' not found")

    course_title = analysis.syllabus.title if analysis.syllabus else "Curriculum Course"

    # 2. Extract candidate items
    missing_items = [it for it in analysis.items if it.kind == "missing"]
    obsolete_items = [it for it in analysis.items if it.kind == "obsolete"]

    # 3. Calculate 30-day trends for missing candidates to highlight emerging skills
    trend_cutoff = datetime.now(UTC).date() - timedelta(days=trend_days)
    missing_ids = [it.skill_id for it in missing_items]

    trends_by_skill: dict[uuid.UUID, float] = {}
    if missing_ids:
        snap_stmt = (
            select(
                SkillDemandDaily.skill_id,
                SkillDemandDaily.demand_pct,
            )
            .where(
                SkillDemandDaily.skill_id.in_(missing_ids),
                SkillDemandDaily.day >= trend_cutoff,
            )
            .order_by(SkillDemandDaily.skill_id, SkillDemandDaily.day.asc())
        )
        snap_res = await db.execute(snap_stmt)
        snaps = snap_res.all()

        history: dict[uuid.UUID, list[float]] = {}
        for sid, dpct in snaps:
            history.setdefault(sid, []).append(dpct)

        for sid, pts in history.items():
            if len(pts) >= 2:
                trends_by_skill[sid] = round(pts[-1] - pts[0], 4)
            elif len(pts) == 1:
                trends_by_skill[sid] = 0.0

    # Sort missing items by demand_pct and trend_pct
    missing_items.sort(
        key=lambda it: (it.demand_pct, trends_by_skill.get(it.skill_id, 0.0)),
        reverse=True,
    )
    add_candidates = missing_items[:max_add]

    # Sort obsolete items by demand_pct ascending (0 demand first)
    obsolete_items.sort(key=lambda it: it.demand_pct)
    drop_candidates = obsolete_items[:max_drop]

    # 4. Prepare data strings for LLM prompting
    missing_info_lines = [
        f"- {it.skill.canonical_name} ({it.skill.category or 'General'}): "
        f"{it.demand_pct * 100:.1f}% market demand, "
        f"trend: {trends_by_skill.get(it.skill_id, 0.0) * 100:+.1f}%"
        for it in add_candidates
        if it.skill
    ]
    missing_info = "\n".join(missing_info_lines) or "None identified."

    obsolete_info_lines = [
        f"- {it.skill.canonical_name} ({it.skill.category or 'General'}): "
        f"{it.demand_pct * 100:.1f}% market demand"
        for it in drop_candidates
        if it.skill
    ]
    obsolete_info = "\n".join(obsolete_info_lines) or "None identified."

    user_prompt = RECOMMENDATIONS_USER_TEMPLATE.format(
        course_title=course_title,
        role_query=analysis.role_query,
        location=analysis.location,
        gap_pct=analysis.gap_pct,
        coverage_pct=analysis.coverage_pct,
        missing_skills_info=missing_info,
        obsolete_skills_info=obsolete_info,
    )

    llm_data: dict = {}
    if llm_provider is not None:
        try:
            raw_result = await llm_provider.extract_json(
                prompt=user_prompt,
                system_instruction=SYSTEM_INSTRUCTION_RECOMMENDATIONS,
            )
            if isinstance(raw_result, dict):
                llm_data = raw_result
        except Exception as e:
            logger.warning(
                "LLM recommendation generation failed, falling back to rule-based: %s",
                e,
            )

    # 5. Build final structured recommendation items
    llm_add_map = {
        item.get("name", "").strip().lower(): item
        for item in llm_data.get("skills_to_add", [])
        if isinstance(item, dict) and "name" in item
    }
    llm_drop_map = {
        item.get("name", "").strip().lower(): item
        for item in llm_data.get("skills_to_drop", [])
        if isinstance(item, dict) and "name" in item
    }

    skills_to_add: list[SkillRecommendationItem] = []
    for it in add_candidates:
        if not it.skill:
            continue
        norm_name = it.skill.canonical_name.strip().lower()
        llm_match = llm_add_map.get(norm_name)

        if llm_match:
            rationale = str(
                llm_match.get("rationale")
                or f"High market demand ({it.demand_pct * 100:.1f}%)."
            )
            module = str(
                llm_match.get("suggested_module")
                or f"Modern {it.skill.category or 'Technology'} Practices"
            )
            weeks = int(llm_match.get("suggested_weeks") or 2)
        else:
            rationale = (
                f"High industry demand ({it.demand_pct * 100:.1f}%) observed in "
                f"{analysis.role_query} roles."
            )
            module = f"Applied {it.skill.category or 'Core'} Methodologies"
            weeks = 2

        skills_to_add.append(
            SkillRecommendationItem(
                skill_id=it.skill_id,
                skill_name=it.skill.canonical_name,
                category=it.skill.category,
                action=SkillRecommendationAction.ADD,
                demand_pct=it.demand_pct,
                trend_pct=trends_by_skill.get(it.skill_id, 0.0),
                rationale=rationale,
                suggested_module=module,
                suggested_weeks=weeks,
            )
        )

    skills_to_drop: list[SkillRecommendationItem] = []
    for it in drop_candidates:
        if not it.skill:
            continue
        norm_name = it.skill.canonical_name.strip().lower()
        llm_match = llm_drop_map.get(norm_name)

        if llm_match:
            rationale = str(
                llm_match.get("rationale")
                or f"Low industry demand ({it.demand_pct * 100:.1f}%)."
            )
        else:
            rationale = (
                f"Observed market demand is {it.demand_pct * 100:.1f}%, "
                "below curriculum relevance threshold. "
                "Recommend phasing out to free up instructional credits."
            )

        skills_to_drop.append(
            SkillRecommendationItem(
                skill_id=it.skill_id,
                skill_name=it.skill.canonical_name,
                category=it.skill.category,
                action=SkillRecommendationAction.DROP,
                demand_pct=it.demand_pct,
                trend_pct=0.0,
                rationale=rationale,
                suggested_module="",
                suggested_weeks=0,
            )
        )

    summary = llm_data.get("summary") or (
        f"Curriculum analysis indicates a {analysis.gap_pct:.1f}% gap compared to "
        f"market demand for {analysis.role_query} in {analysis.location}. "
        f"Adopting {len(skills_to_add)} prioritized technical skills and phasing out "
        f"{len(skills_to_drop)} low-demand topics will optimize student readiness."
    )

    return CurriculumRecommendationsResponse(
        analysis_id=analysis.id,
        syllabus_id=analysis.syllabus_id,
        course_title=course_title,
        role_query=analysis.role_query,
        location=analysis.location,
        gap_pct=analysis.gap_pct,
        coverage_pct=analysis.coverage_pct,
        skills_to_add=skills_to_add,
        skills_to_drop=skills_to_drop,
        summary=summary,
    )
