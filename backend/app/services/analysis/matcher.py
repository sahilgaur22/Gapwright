import logging
import math
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.skill import Skill
from app.schemas.analysis import MatchType, SkillMatchResult
from app.services.skills.normalizer import ALIAS_MAP

logger = logging.getLogger(__name__)


def compute_cosine_similarity(
    vec_a: list[float] | Any | None,
    vec_b: list[float] | Any | None,
) -> float:
    """Compute cosine similarity between two numeric vectors."""
    if vec_a is None or vec_b is None:
        return 0.0

    try:
        a = list(vec_a)
        b = list(vec_b)
    except Exception:
        return 0.0

    if not a or not b or len(a) != len(b):
        return 0.0

    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    sim = dot / (norm_a * norm_b)
    # Bound within [-1.0, 1.0] to account for float inaccuracy
    return max(-1.0, min(1.0, float(sim)))


def is_alias_match(
    name_a: str,
    aliases_a: list[str] | None,
    name_b: str,
    aliases_b: list[str] | None,
) -> bool:
    """Check if two skills match via canonical names or configured aliases."""
    clean_a = name_a.strip().lower()
    clean_b = name_b.strip().lower()

    if clean_a == clean_b:
        return True

    # Check via ALIAS_MAP
    root_a = ALIAS_MAP.get(clean_a, clean_a)
    root_b = ALIAS_MAP.get(clean_b, clean_b)
    if root_a.lower() == root_b.lower():
        return True

    # Check cross-alias sets
    set_a = {clean_a}
    if aliases_a:
        set_a.update(a.strip().lower() for a in aliases_a if a)

    set_b = {clean_b}
    if aliases_b:
        set_b.update(b.strip().lower() for b in aliases_b if b)

    return bool(set_a.intersection(set_b))


def match_single_skill(
    syllabus_skill: Skill,
    market_skills: list[Skill],
    threshold: float = settings.SKILL_MATCH_THRESHOLD,
) -> SkillMatchResult | None:
    """Find the best match for an academic skill among market skills."""
    norm_s_name = syllabus_skill.canonical_name.strip().lower()

    # 1. Exact match
    for m in market_skills:
        if m.canonical_name.strip().lower() == norm_s_name:
            return SkillMatchResult(
                syllabus_skill_id=syllabus_skill.id,
                syllabus_skill_name=syllabus_skill.canonical_name,
                market_skill_id=m.id,
                market_skill_name=m.canonical_name,
                similarity=1.0,
                match_type=MatchType.EXACT,
            )

    # 2. Alias match
    for m in market_skills:
        if is_alias_match(
            syllabus_skill.canonical_name,
            syllabus_skill.aliases,
            m.canonical_name,
            m.aliases,
        ):
            return SkillMatchResult(
                syllabus_skill_id=syllabus_skill.id,
                syllabus_skill_name=syllabus_skill.canonical_name,
                market_skill_id=m.id,
                market_skill_name=m.canonical_name,
                similarity=1.0,
                match_type=MatchType.ALIAS,
            )

    # 3. Semantic / Vector nearest-neighbour match
    if syllabus_skill.embedding is not None:
        best_match: Skill | None = None
        best_sim = -1.0

        for m in market_skills:
            if m.embedding is not None:
                sim = compute_cosine_similarity(syllabus_skill.embedding, m.embedding)
                if sim > best_sim:
                    best_sim = sim
                    best_match = m

        if best_match is not None and best_sim >= threshold:
            return SkillMatchResult(
                syllabus_skill_id=syllabus_skill.id,
                syllabus_skill_name=syllabus_skill.canonical_name,
                market_skill_id=best_match.id,
                market_skill_name=best_match.canonical_name,
                similarity=round(best_sim, 4),
                match_type=MatchType.SEMANTIC,
            )

    return None


def match_skills(
    syllabus_skills: list[Skill],
    market_skills: list[Skill],
    threshold: float = settings.SKILL_MATCH_THRESHOLD,
) -> list[SkillMatchResult]:
    """Match all syllabus skills against available market skills."""
    matches: list[SkillMatchResult] = []
    for s in syllabus_skills:
        matched = match_single_skill(s, market_skills, threshold=threshold)
        if matched is not None:
            matches.append(matched)
    return matches


match_all_skills = match_skills


async def find_semantic_matches_in_db(
    db: AsyncSession,
    target_skill: Skill,
    limit: int = 5,
    threshold: float = settings.SKILL_MATCH_THRESHOLD,
) -> list[tuple[Skill, float]]:
    """Query nearest-neighbour skill matches in the database using vector embeddings."""
    if target_skill.embedding is None:
        return []

    # Check database dialect
    bind = db.bind
    dialect_name = bind.dialect.name if bind else ""

    if dialect_name == "postgresql":
        # Native pgvector cosine distance
        distance_col = target_skill.embedding.cosine_distance(Skill.embedding)
        stmt = (
            select(Skill, (1.0 - distance_col).label("similarity"))
            .where(
                Skill.id != target_skill.id,
                Skill.embedding.isnot(None),
            )
            .order_by(distance_col.asc())
            .limit(limit)
        )
        res = await db.execute(stmt)
        rows = res.all()
        return [
            (skill, float(round(sim, 4))) for skill, sim in rows if sim >= threshold
        ]

    # In-memory fallback (e.g. SQLite test engine)
    all_skills_stmt = select(Skill).where(
        Skill.id != target_skill.id,
        Skill.embedding.isnot(None),
    )
    all_res = await db.execute(all_skills_stmt)
    all_candidates = all_res.scalars().all()

    scored: list[tuple[Skill, float]] = []
    for cand in all_candidates:
        sim = compute_cosine_similarity(target_skill.embedding, cand.embedding)
        if sim >= threshold:
            scored.append((cand, round(sim, 4)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]
