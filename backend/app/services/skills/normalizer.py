import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.skill import Skill
from app.schemas.skill import SkillExtractionItem
from app.services.llm.base import LLMProvider
from app.services.skills.taxonomy import SEED_TAXONOMY

logger = logging.getLogger(__name__)

# Compile quick in-memory lookup dictionary for fast resolution of known aliases
ALIAS_MAP: dict[str, str] = {}
for entry in SEED_TAXONOMY:
    canonical = entry["name"]
    ALIAS_MAP[canonical.lower()] = canonical
    for alias in entry["aliases"]:
        ALIAS_MAP[alias.lower()] = canonical


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=False))
    norm_a = sum(a * a for a in vec_a) ** 0.5
    norm_b = sum(b * b for b in vec_b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


async def seed_skills_taxonomy(
    db: AsyncSession,
    embed_provider: LLMProvider | None = None,
) -> int:
    """Seed the standard taxonomy of tech skills into the database if not present."""
    count = 0
    for entry in SEED_TAXONOMY:
        existing = await db.execute(
            select(Skill).where(
                func.lower(Skill.canonical_name) == entry["name"].lower()
            )
        )
        if existing.scalar_one_or_none() is not None:
            continue

        embedding_vector = None
        if embed_provider:
            try:
                emb = await embed_provider.embed(entry["name"])
                if isinstance(emb, list) and emb and isinstance(emb[0], (int, float)):
                    embedding_vector = emb
            except Exception as exc:
                logger.warning(f"Failed to embed seed skill {entry['name']}: {exc}")

        skill = Skill(
            id=uuid.uuid4(),
            canonical_name=entry["name"],
            category=entry["category"],
            aliases=entry["aliases"],
            embedding=embedding_vector,
        )
        db.add(skill)
        count += 1

    if count > 0:
        await db.commit()

    return count


async def normalize_skill(
    name: str,
    category: str | None,
    db: AsyncSession,
    *,
    embed_provider: LLMProvider | None = None,
    threshold: float = settings.SKILL_MATCH_THRESHOLD,
) -> Skill:
    """Normalize a skill mention into a canonical taxonomy Skill node.

    Lookup hierarchy:
        1. In-memory alias dictionary mapping (e.g. 'k8s' -> 'Kubernetes')
        2. Database exact match on canonical_name or existing aliases
        3. Vector embedding cosine similarity lookup (>= threshold)
        4. If no match meets threshold, creates and stores a new canonical Skill node.
    """
    clean_name = name.strip()
    lower_name = clean_name.lower()

    # Step 1: Check in-memory alias dictionary
    resolved_canonical = ALIAS_MAP.get(lower_name, clean_name)
    target_lower = resolved_canonical.lower()

    # Step 2: Database lookup by canonical name
    query = select(Skill).where(func.lower(Skill.canonical_name) == target_lower)
    result = await db.execute(query)
    matched_skill = result.scalar_one_or_none()

    if matched_skill:
        return matched_skill

    # Step 2b: Database lookup through all existing skill aliases
    all_skills_res = await db.execute(select(Skill))
    all_skills = list(all_skills_res.scalars().all())

    for skill in all_skills:
        aliases_lower = [a.lower() for a in (skill.aliases or [])]
        if lower_name in aliases_lower or target_lower in aliases_lower:
            return skill

    # Step 3: Semantic embedding cosine similarity match
    query_vector: list[float] | None = None
    if embed_provider:
        try:
            emb = await embed_provider.embed(clean_name)
            if isinstance(emb, list) and emb and isinstance(emb[0], (int, float)):
                # Cast elements to float
                query_vector = [float(x) for x in emb if isinstance(x, (int, float))]
        except Exception as exc:
            logger.warning(
                f"Embedding failed during normalization for {clean_name}: {exc}"
            )

    if query_vector:
        best_match: Skill | None = None
        best_similarity = -1.0

        for skill in all_skills:
            if skill.embedding:
                skill_vec = [float(x) for x in skill.embedding]
                sim = cosine_similarity(query_vector, skill_vec)
                if sim > best_similarity:
                    best_similarity = sim
                    best_match = skill

        if best_match and best_similarity >= threshold:
            logger.info(
                f"Merged '{clean_name}' into '{best_match.canonical_name}' "
                f"(cosine similarity: {best_similarity:.4f} >= {threshold})"
            )
            # Add alias to matched skill if not present
            current_aliases = list(best_match.aliases or [])
            if lower_name not in [a.lower() for a in current_aliases]:
                current_aliases.append(clean_name)
                best_match.aliases = current_aliases
                db.add(best_match)
                await db.commit()
                await db.refresh(best_match)
            return best_match

    # Step 4: No match meeting threshold -> create a new canonical skill
    new_skill = Skill(
        id=uuid.uuid4(),
        canonical_name=resolved_canonical,
        category=category,
        aliases=[clean_name],
        embedding=query_vector,
    )
    db.add(new_skill)
    await db.commit()
    await db.refresh(new_skill)
    return new_skill


async def normalize_skills_batch(
    extracted_skills: list[SkillExtractionItem],
    db: AsyncSession,
    *,
    embed_provider: LLMProvider | None = None,
    threshold: float = settings.SKILL_MATCH_THRESHOLD,
) -> list[tuple[Skill, SkillExtractionItem]]:
    """Normalize a list of extracted skills, associating each with its canonical

    Skill node in the database.
    """
    normalized_pairs: list[tuple[Skill, SkillExtractionItem]] = []
    for item in extracted_skills:
        skill_node = await normalize_skill(
            name=item.name,
            category=item.category,
            db=db,
            embed_provider=embed_provider,
            threshold=threshold,
        )
        normalized_pairs.append((skill_node, item))
    return normalized_pairs
