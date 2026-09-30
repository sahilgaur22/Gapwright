"""Reports and exports API endpoints."""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.analysis import Analysis, AnalysisItem
from app.db.models.syllabus import Syllabus
from app.db.session import get_db
from app.services.analysis.recommendations import generate_curriculum_recommendations
from app.services.llm import get_llm_provider
from app.services.reports.export import generate_csv_report, generate_pdf_report

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports & Exports"])


@router.get("/{analysis_id}/export")
async def export_analysis_report(
    analysis_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    format: Annotated[str, Query(description="Export format: 'csv' or 'pdf'")] = "csv",
) -> Response:
    """Export a curriculum gap analysis report in CSV or PDF format."""
    fmt = format.lower().strip()
    if fmt not in ("csv", "pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported format '{format}'. Supported formats are 'csv' and 'pdf'."
            ),
        )

    # Load Analysis with items and skill details
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

    # Load related Syllabus with institution
    syl_res = await db.execute(
        select(Syllabus)
        .options(selectinload(Syllabus.institution))
        .where(Syllabus.id == analysis.syllabus_id)
    )
    syllabus = syl_res.scalar_one_or_none()

    if fmt == "csv":
        csv_bytes = generate_csv_report(analysis=analysis, syllabus=syllabus)
        filename = f"gapwright-analysis-{analysis_id}.csv"
        return Response(
            content=csv_bytes,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    # Format == "pdf"
    # Attempt to load recommendations for inclusion
    recs = None
    try:
        provider = None
        try:
            provider = get_llm_provider()
        except Exception:
            provider = None

        recs = await generate_curriculum_recommendations(
            db=db,
            analysis_id=analysis_id,
            llm_provider=provider,
            max_add=4,
            max_drop=3,
        )
    except Exception as e:
        logger.warning("Could not generate recommendations for PDF report: %s", str(e))
        recs = None

    pdf_bytes = generate_pdf_report(
        analysis=analysis, syllabus=syllabus, recommendations=recs
    )
    filename = f"gapwright-analysis-{analysis_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
