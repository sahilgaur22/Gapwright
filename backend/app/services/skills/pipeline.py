import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.syllabus import Syllabus, SyllabusSkill
from app.db.session import AsyncSessionLocal
from app.services.llm.base import LLMProvider
from app.services.llm.factory import get_llm_provider
from app.services.skills.extractor import extract_skills_from_document
from app.services.skills.normalizer import normalize_skills_batch

logger = logging.getLogger(__name__)


async def _execute_pipeline(
    syllabus_id: uuid.UUID,
    db: AsyncSession,
    *,
    provider: LLMProvider | None = None,
    threshold: float = settings.SKILL_MATCH_THRESHOLD,
) -> Syllabus:
    """Internal execution of syllabus processing pipeline on an open DB session."""
    query = select(Syllabus).where(Syllabus.id == syllabus_id)
    result = await db.execute(query)
    syllabus = result.scalar_one_or_none()

    if not syllabus:
        logger.error(f"Syllabus {syllabus_id} not found for skill processing pipeline")
        raise ValueError(f"Syllabus with ID '{syllabus_id}' not found")

    # Step 1: Transition status to processing
    syllabus.status = "processing"
    syllabus.error_message = None
    db.add(syllabus)
    await db.commit()
    await db.refresh(syllabus)

    try:
        # Resolve LLM provider if not injected
        if provider is None:
            provider = get_llm_provider()

        # Step 2: Extract skills from raw syllabus text using chunked extraction
        extraction_result = await extract_skills_from_document(
            syllabus.raw_text,
            provider=provider,
        )

        # Step 3: Normalize extracted skills against taxonomy and database
        normalized_pairs = await normalize_skills_batch(
            extraction_result.skills,
            db=db,
            embed_provider=provider,
            threshold=threshold,
        )

        # Step 4: Persist syllabus-skill associations
        for skill_node, item in normalized_pairs:
            assoc_query = select(SyllabusSkill).where(
                SyllabusSkill.syllabus_id == syllabus.id,
                SyllabusSkill.skill_id == skill_node.id,
            )
            assoc_res = await db.execute(assoc_query)
            existing_assoc = assoc_res.scalar_one_or_none()

            if existing_assoc:
                if item.confidence > existing_assoc.confidence:
                    existing_assoc.confidence = item.confidence
                    existing_assoc.evidence = item.evidence
                    db.add(existing_assoc)
            else:
                new_assoc = SyllabusSkill(
                    syllabus_id=syllabus.id,
                    skill_id=skill_node.id,
                    evidence=item.evidence,
                    confidence=item.confidence,
                )
                db.add(new_assoc)

        # Step 5: Transition status to ready
        syllabus.status = "ready"
        syllabus.error_message = None
        db.add(syllabus)
        await db.commit()
        await db.refresh(syllabus)
        logger.info(
            f"Syllabus {syllabus_id} processed with {len(normalized_pairs)} skills"
        )
        return syllabus

    except Exception as exc:
        logger.exception(
            f"Syllabus processing pipeline failed for {syllabus_id}: {exc}"
        )
        await db.rollback()

        # Transition status to failed and record error message
        try:
            fail_query = select(Syllabus).where(Syllabus.id == syllabus_id)
            fail_res = await db.execute(fail_query)
            failed_syllabus = fail_res.scalar_one_or_none()
            if failed_syllabus:
                failed_syllabus.status = "failed"
                failed_syllabus.error_message = str(exc)
                db.add(failed_syllabus)
                await db.commit()
                await db.refresh(failed_syllabus)
                return failed_syllabus
        except Exception as update_err:
            logger.error(
                f"Failed to record failure for syllabus {syllabus_id}: {update_err}"
            )

        raise


async def process_syllabus_pipeline(
    syllabus_id: uuid.UUID,
    *,
    db: AsyncSession | None = None,
    provider: LLMProvider | None = None,
    threshold: float = settings.SKILL_MATCH_THRESHOLD,
) -> Syllabus:
    """Execute asynchronous skill extraction and normalization pipeline.

    Pipeline stages:
      1. Transition syllabus status to 'processing'
      2. Chunk text and extract skills via LLM provider
      3. Normalize extracted skills to canonical taxonomy nodes
      4. Persist syllabus-skill associations with evidence and confidence
      5. Transition syllabus status to 'ready' (or 'failed' on error)

    Args:
        syllabus_id: Target syllabus UUID.
        db: Optional active AsyncSession. If omitted, opens AsyncSessionLocal.
        provider: Optional LLMProvider. If omitted, uses default provider.
        threshold: Vector similarity threshold for skill normalization.

    Returns:
        The updated Syllabus record with status 'ready' or 'failed'.
    """
    if db is not None:
        return await _execute_pipeline(
            syllabus_id=syllabus_id,
            db=db,
            provider=provider,
            threshold=threshold,
        )

    async with AsyncSessionLocal() as session:
        return await _execute_pipeline(
            syllabus_id=syllabus_id,
            db=session,
            provider=provider,
            threshold=threshold,
        )
