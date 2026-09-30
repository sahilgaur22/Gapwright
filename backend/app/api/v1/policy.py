from collections import defaultdict
from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import require_role
from app.db.models.analysis import Analysis, AnalysisItem
from app.db.models.syllabus import Syllabus
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.policy import (
    InstitutionAlignmentSummary,
    PolicyOverviewResponse,
    RoleMarketComparison,
    SystemicSkillGap,
)


@dataclass
class _SkillAccumulator:
    occurrences: int = 0
    demand_sum: float = 0.0
    postings_sum: int = 0
    category: str | None = None


router = APIRouter(prefix="/policy", tags=["Policymaker Overview"])


@router.get("/overview", response_model=PolicyOverviewResponse)
async def get_policymaker_overview(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("admin", "policymaker"))],
) -> PolicyOverviewResponse:
    """Retrieve systemic curriculum gap statistics across institutions and roles.

    Access is restricted to policymaker and administrative accounts.
    """
    # 1. Fetch all analyses with items and associated syllabus
    stmt = select(Analysis).options(
        selectinload(Analysis.items).selectinload(AnalysisItem.skill),
    )
    res = await db.execute(stmt)
    analyses = list(res.scalars().all())

    # Fetch syllabi mapping with institution attribution
    syl_stmt = select(Syllabus).options(selectinload(Syllabus.institution))
    syl_res = await db.execute(syl_stmt)
    syllabi_map = {s.id: s for s in syl_res.scalars().all()}

    if not analyses:
        return PolicyOverviewResponse(
            total_analyses=0,
            total_institutions=0,
            average_gap_pct=0.0,
            average_coverage_pct=0.0,
            top_systemic_missing_skills=[],
            institutions=[],
            roles=[],
        )

    total_analyses = len(analyses)
    total_gap = sum(a.gap_pct for a in analyses)
    total_coverage = sum(a.coverage_pct for a in analyses)
    avg_gap = round(total_gap / total_analyses, 1)
    avg_cov = round(total_coverage / total_analyses, 1)

    # 2. Institution groupings
    inst_data: dict[str, list[Analysis]] = defaultdict(list)
    for a in analyses:
        syl = syllabi_map.get(a.syllabus_id)
        inst_name = (
            syl.institution.name.strip()
            if syl and syl.institution
            else "Independent Technical Institute"
        )
        inst_data[inst_name].append(a)

    institutions_list: list[InstitutionAlignmentSummary] = []
    for inst, inst_analyses in inst_data.items():
        n = len(inst_analyses)
        i_gap = round(sum(x.gap_pct for x in inst_analyses) / n, 1)
        i_cov = round(sum(x.coverage_pct for x in inst_analyses) / n, 1)
        institutions_list.append(
            InstitutionAlignmentSummary(
                institution=inst,
                evaluations_count=n,
                average_gap_pct=i_gap,
                average_coverage_pct=i_cov,
            )
        )
    institutions_list.sort(key=lambda x: x.average_gap_pct, reverse=True)

    # 3. Role groupings
    role_data: dict[str, list[Analysis]] = defaultdict(list)
    for a in analyses:
        role_data[a.role_query.strip()].append(a)

    roles_list: list[RoleMarketComparison] = []
    for role_name, r_analyses in role_data.items():
        rn = len(r_analyses)
        r_gap = round(sum(x.gap_pct for x in r_analyses) / rn, 1)
        r_cov = round(sum(x.coverage_pct for x in r_analyses) / rn, 1)
        roles_list.append(
            RoleMarketComparison(
                role=role_name,
                evaluations_count=rn,
                average_gap_pct=r_gap,
                average_coverage_pct=r_cov,
            )
        )
    roles_list.sort(key=lambda x: x.evaluations_count, reverse=True)

    # 4. Systemic missing skills aggregations
    missing_skill_stats: dict[str, _SkillAccumulator] = defaultdict(_SkillAccumulator)

    for a in analyses:
        for it in a.items:
            if it.kind == "missing":
                name = it.skill.canonical_name if it.skill else "Unknown Skill"
                cat = it.skill.category if it.skill else None
                entry = missing_skill_stats[name]
                entry.occurrences += 1
                entry.demand_sum += it.demand_pct
                entry.postings_sum += it.demand_count
                if cat and not entry.category:
                    entry.category = cat

    top_missing: list[SystemicSkillGap] = []
    for s_name, entry in missing_skill_stats.items():
        occ = entry.occurrences
        avg_demand = round(entry.demand_sum / occ, 1)
        tot_postings = entry.postings_sum
        top_missing.append(
            SystemicSkillGap(
                skill_name=s_name,
                category=entry.category,
                occurrences=occ,
                average_demand_pct=avg_demand,
                total_postings=tot_postings,
            )
        )

    # Sort systemic gaps by occurrences then average demand
    top_missing.sort(key=lambda x: (x.occurrences, x.average_demand_pct), reverse=True)

    return PolicyOverviewResponse(
        total_analyses=total_analyses,
        total_institutions=len(institutions_list),
        average_gap_pct=avg_gap,
        average_coverage_pct=avg_cov,
        top_systemic_missing_skills=top_missing[:15],
        institutions=institutions_list,
        roles=roles_list,
    )
