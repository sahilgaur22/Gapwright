import json
import logging
from typing import Any

from pydantic import ValidationError

from app.schemas.skill import SkillExtractionItem, SkillExtractionResult
from app.services.llm.base import LLMProvider
from app.services.llm.exceptions import ModelResponseError
from app.services.llm.prompts import (
    SKILL_EXTRACTION_USER_TEMPLATE,
    SKILL_REPAIR_USER_TEMPLATE,
    SYSTEM_INSTRUCTION_SKILL_EXTRACTION,
    SYSTEM_INSTRUCTION_SKILL_REPAIR,
)
from app.services.skills.chunking import SectionChunker
from app.services.skills.merger import merge_and_deduplicate_skills

logger = logging.getLogger(__name__)


def _validate_raw_extraction(raw_data: Any) -> SkillExtractionResult:
    """Validate raw parsed JSON dictionary or list into SkillExtractionResult."""
    if isinstance(raw_data, list):
        items = [SkillExtractionItem.model_validate(item) for item in raw_data]
        return SkillExtractionResult(skills=items)
    if isinstance(raw_data, dict):
        if "skills" in raw_data:
            return SkillExtractionResult.model_validate(raw_data)
        # In case the model emitted a single skill dict
        if "name" in raw_data and "category" in raw_data:
            return SkillExtractionResult(
                skills=[SkillExtractionItem.model_validate(raw_data)]
            )
        return SkillExtractionResult.model_validate(raw_data)
    raise ValueError(f"Expected dict or list from LLM, got {type(raw_data).__name__}")


async def extract_skills_from_text(
    text: str,
    provider: LLMProvider,
    *,
    max_repair_retries: int = 1,
) -> SkillExtractionResult:
    """Extract structured skills from a text snippet using the given LLM provider,

    validating output against the Pydantic schema and performing a repair retry
    if the first response is malformed.

    Args:
        text: Input document text or chunk.
        provider: LLMProvider instance (Gemini or Groq).
        max_repair_retries: Number of repair attempts on validation failure (default 1).

    Returns:
        Validated SkillExtractionResult containing the extracted skills.

    Raises:
        ModelResponseError: If the extraction fails and cannot be repaired.
    """
    cleaned_text = text.strip()
    if not cleaned_text:
        return SkillExtractionResult(skills=[])

    prompt = SKILL_EXTRACTION_USER_TEMPLATE.format(text=cleaned_text)
    raw_response = await provider.extract_json(
        prompt,
        system_instruction=SYSTEM_INSTRUCTION_SKILL_EXTRACTION,
    )

    try:
        return _validate_raw_extraction(raw_response)
    except (ValidationError, ValueError) as err:
        logger.warning(
            f"Skill extraction validation failed on initial output ({err}). "
            f"Attempting repair (remaining retries: {max_repair_retries})..."
        )

        if max_repair_retries <= 0:
            raise ModelResponseError(
                f"Skill extraction failed schema validation: {err}"
            ) from err

        # Perform repair retry
        repair_prompt = SKILL_REPAIR_USER_TEMPLATE.format(
            errors=str(err),
            raw_output=json.dumps(raw_response, default=str),
        )

        repaired_response = await provider.extract_json(
            repair_prompt,
            system_instruction=SYSTEM_INSTRUCTION_SKILL_REPAIR,
        )

        try:
            return _validate_raw_extraction(repaired_response)
        except (ValidationError, ValueError) as repair_err:
            logger.error(
                f"Skill extraction repair failed schema validation: {repair_err}"
            )
            raise ModelResponseError(
                f"Skill extraction failed schema validation after repair: {repair_err}"
            ) from repair_err


async def extract_skills_from_document(
    text: str,
    provider: LLMProvider,
    *,
    max_chunk_tokens: int = SectionChunker.DEFAULT_MAX_CHUNK_TOKENS,
    overlap_tokens: int = SectionChunker.DEFAULT_OVERLAP_TOKENS,
    max_repair_retries: int = 1,
) -> SkillExtractionResult:
    """Extract, aggregate, and deduplicate skills from long syllabus documents.

    Uses section-aware chunking to break lengthy documents into pieces,
    extracts skills per chunk with validation and repair, and then merges and
    deduplicates all extracted skills.
    """
    cleaned_text = text.strip()
    if not cleaned_text:
        return SkillExtractionResult(skills=[])

    chunks = SectionChunker.chunk_document(
        cleaned_text,
        max_chunk_tokens=max_chunk_tokens,
        overlap_tokens=overlap_tokens,
    )

    if not chunks:
        return SkillExtractionResult(skills=[])

    # If only one chunk, single extraction is sufficient
    if len(chunks) == 1:
        return await extract_skills_from_text(
            chunks[0],
            provider,
            max_repair_retries=max_repair_retries,
        )

    # Multi-chunk processing
    all_extracted_skills: list[SkillExtractionItem] = []
    for chunk in chunks:
        result = await extract_skills_from_text(
            chunk,
            provider,
            max_repair_retries=max_repair_retries,
        )
        all_extracted_skills.extend(result.skills)

    # Merge and deduplicate across all chunks
    merged = merge_and_deduplicate_skills(all_extracted_skills)
    return SkillExtractionResult(skills=merged)
