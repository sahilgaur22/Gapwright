import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.analysis import Analysis, AnalysisItem
from app.db.session import get_db
from app.schemas.analysis import (
    AnalysisCreateRequest,
    AnalysisItemKind,
    AnalysisItemRead,
    AnalysisRead,
    CurriculumRecommendationsResponse,
)
from app.services.analysis.gap import compute_gap_analysis
from app.services.analysis.recommendations import generate_curriculum_recommendations
from app.services.llm import get_llm_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["Gap Analysis"])


def _to_analysis_read(analysis: Analysis) -> AnalysisRead:
    items_read: list[AnalysisItemRead] = []
    for it in analysis.items:
        items_read.append(
            AnalysisItemRead(
                skill_id=it.skill_id,
                skill_name=it.skill.canonical_name if it.skill else "",
                category=it.skill.category if it.skill else None,
                kind=AnalysisItemKind(it.kind),
                demand_count=it.demand_count,
                demand_pct=it.demand_pct,
                rank=it.rank or 0,
            )
        )

    return AnalysisRead(
        id=analysis.id,
        syllabus_id=analysis.syllabus_id,
        role_query=analysis.role_query,
        location=analysis.location,
        gap_pct=analysis.gap_pct,
        coverage_pct=analysis.coverage_pct,
        created_at=analysis.created_at,
        items=items_read,
    )


@router.post("", response_model=AnalysisRead, status_code=status.HTTP_201_CREATED)
async def create_analysis(
    request: AnalysisCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnalysisRead:
    """Run curriculum gap analysis against live job market postings."""
    try:
        analysis = await compute_gap_analysis(
            db=db,
            syllabus_id=request.syllabus_id,
            role_query=request.role_query,
            location=request.location,
            remote_only=request.remote_only,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Failed to compute gap analysis: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gap analysis calculation failed: {str(e)}",
        ) from e

    return _to_analysis_read(analysis)


@router.get("/{analysis_id}", response_model=AnalysisRead)
async def get_analysis(
    analysis_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnalysisRead:
    """Retrieve details, gap percentage, and categorized skills for an analysis."""
    stmt = (
        select(Analysis)
        .options(
            selectinload(Analysis.items).selectinload(AnalysisItem.skill),
        )
        .where(Analysis.id == analysis_id)
    )
    res = await db.execute(stmt)
    analysis = res.scalar_one_or_none()
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID '{analysis_id}' not found",
        )

    return _to_analysis_read(analysis)


@router.get("", response_model=list[AnalysisRead])
async def list_analyses(
    db: Annotated[AsyncSession, Depends(get_db)],
    syllabus_id: Annotated[
        uuid.UUID | None, Query(description="Filter by syllabus")
    ] = None,
) -> list[AnalysisRead]:
    """List historical curriculum gap analyses."""
    stmt = select(Analysis).options(
        selectinload(Analysis.items).selectinload(AnalysisItem.skill),
    )
    if syllabus_id is not None:
        stmt = stmt.where(Analysis.syllabus_id == syllabus_id)

    stmt = stmt.order_by(Analysis.created_at.desc())
    res = await db.execute(stmt)
    analyses = list(res.scalars().all())
    return [_to_analysis_read(a) for a in analyses]


@router.get(
    "/{analysis_id}/recommendations",
    response_model=CurriculumRecommendationsResponse,
)
async def get_recommendations(
    analysis_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    max_add: Annotated[int, Query(ge=1, le=20)] = 5,
    max_drop: Annotated[int, Query(ge=1, le=20)] = 5,
) -> CurriculumRecommendationsResponse:
    """Generate grounded, actionable curriculum recommendations for an analysis."""
    provider = None
    try:
        provider = get_llm_provider()
    except Exception:
        provider = None

    try:
        return await generate_curriculum_recommendations(
            db=db,
            analysis_id=analysis_id,
            llm_provider=provider,
            max_add=max_add,
            max_drop=max_drop,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Failed to generate recommendations: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recommendations generation failed: {str(e)}",
        ) from e
