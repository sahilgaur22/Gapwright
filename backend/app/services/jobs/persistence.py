import hashlib
import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.job import JobPosting, JobSkill
from app.schemas.job import PersistenceResult
from app.services.llm.base import LLMProvider
from app.services.skills.extractor import extract_skills_from_text
from app.services.skills.normalizer import normalize_skill
from app.services.sources.models import RawJob

logger = logging.getLogger(__name__)


def compute_content_hash(
    title: str,
    company: str | None,
    location: str | None,
) -> str:
    """Compute a deterministic hash for title, company, and location.

    Used to detect duplicates across and within sources.
    """
    norm_title = " ".join(title.lower().split())
    norm_company = " ".join((company or "").lower().split())
    norm_loc = " ".join((location or "").lower().split())
    sig = f"{norm_title}|{norm_company}|{norm_loc}"
    return hashlib.sha256(sig.encode("utf-8")).hexdigest()


async def persist_raw_jobs(
    db: AsyncSession,
    raw_jobs: list[RawJob],
    *,
    extract_skills: bool = True,
    llm_provider: LLMProvider | None = None,
    embed_provider: LLMProvider | None = None,
) -> PersistenceResult:
    """Persist a batch of raw jobs with deduplication, upsert, and skill extraction.

    Deduplication rules:
      1. Primary upsert key: (source, external_id). If already present, updates
         last_seen_at and SKIPS LLM skill extraction.
      2. Cross-source content dedupe: title + company (+ city). If identical
         posting is already stored from another source, updates last_seen_at
         and SKIPS LLM skill extraction.
      3. Newly inserted postings undergo LLM skill extraction and canonical
         taxonomy normalization into job_skills.
    """
    result = PersistenceResult()
    now = datetime.now(UTC)

    for raw_job in raw_jobs:
        # Check 1: exact (source, external_id)
        existing_stmt = select(JobPosting).where(
            JobPosting.source == raw_job.source,
            JobPosting.external_id == raw_job.external_id,
        )
        existing_res = await db.execute(existing_stmt)
        existing_posting = existing_res.scalar_one_or_none()

        if existing_posting is not None:
            existing_posting.last_seen_at = now
            existing_posting.is_expired = False
            result.updated_count += 1
            result.skipped_llm_count += 1
            continue

        # Check 2: cross-source content deduplication
        norm_title = raw_job.title.strip().lower()
        norm_company = (raw_job.company or "").strip().lower()

        if norm_company:
            dup_stmt = select(JobPosting).where(
                func.lower(JobPosting.title) == norm_title,
                func.lower(JobPosting.company) == norm_company,
            )
            dup_res = await db.execute(dup_stmt)
            dup_posting = dup_res.scalar_one_or_none()

            if dup_posting is not None:
                dup_posting.last_seen_at = now
                dup_posting.is_expired = False
                result.duplicate_count += 1
                result.skipped_llm_count += 1
                continue

        # Check 3: Insert new job posting
        posting = JobPosting(
            source=raw_job.source,
            external_id=raw_job.external_id,
            title=raw_job.title.strip(),
            company=raw_job.company.strip() if raw_job.company else None,
            location=raw_job.location.strip() if raw_job.location else None,
            description=raw_job.description,
            description_is_truncated=raw_job.description_is_truncated,
            url=raw_job.url,
            posted_at=raw_job.posted_at,
            last_seen_at=now,
        )
        db.add(posting)
        await db.flush()  # populate posting.id
        result.created_count += 1

        # Check 4: Extract skills only for newly inserted postings
        if extract_skills and llm_provider is not None:
            try:
                extraction = await extract_skills_from_text(
                    posting.description,
                    llm_provider,
                )
                for item in extraction.skills:
                    skill_node = await normalize_skill(
                        name=item.name,
                        category=item.category,
                        db=db,
                        embed_provider=embed_provider,
                    )
                    # Check if already linked
                    link_stmt = select(JobSkill).where(
                        JobSkill.job_id == posting.id,
                        JobSkill.skill_id == skill_node.id,
                    )
                    link_res = await db.execute(link_stmt)
                    if link_res.scalar_one_or_none() is None:
                        js = JobSkill(
                            job_id=posting.id,
                            skill_id=skill_node.id,
                            confidence=item.confidence,
                        )
                        db.add(js)
                        result.extracted_skills_count += 1
            except Exception as exc:
                logger.warning(
                    f"Skill extraction failed for job {posting.id} "
                    f"('{posting.title}'): {exc}"
                )

    await db.commit()
    return result
