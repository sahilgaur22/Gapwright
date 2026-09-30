from collections import defaultdict

from app.schemas.skill import SkillExtractionItem


def _choose_best_casing(names: list[str]) -> str:
    """Choose the best formatted casing from a list of equivalent names.

    Prefers MixedCase or TitleCase over all-lowercase or all-uppercase.
    """
    for name in names:
        # If contains both upper and lower (e.g. PyTorch, JavaScript, PostgreSQL)
        if any(c.isupper() for c in name) and any(c.islower() for c in name):
            return name.strip()

    # If any has title case
    for name in names:
        if name.istitle():
            return name.strip()

    # Fallback to first non-empty
    return names[0].strip()


def merge_and_deduplicate_skills(
    skills: list[SkillExtractionItem],
    *,
    max_evidence_snippets: int = 3,
) -> list[SkillExtractionItem]:
    """Merge and deduplicate extracted skill items across multiple chunks.

    Consolidates items by normalized name, retains the highest confidence score,
    reconciles categories, and joins unique evidence snippets.

    Args:
        skills: List of extracted skills from one or more chunks.
        max_evidence_snippets: Maximum number of distinct evidence snippets to preserve.

    Returns:
        Deduplicated list of SkillExtractionItem sorted by confidence descending.
    """
    if not skills:
        return []

    grouped: dict[str, list[SkillExtractionItem]] = defaultdict(list)
    for skill in skills:
        key = skill.name.strip().lower()
        if key:
            grouped[key].append(skill)

    merged: list[SkillExtractionItem] = []

    for _, group in grouped.items():
        # Sort by confidence descending so highest confidence mention comes first
        group.sort(key=lambda s: s.confidence, reverse=True)
        top_mention = group[0]

        best_name = _choose_best_casing([s.name for s in group])
        best_category = top_mention.category
        highest_confidence = top_mention.confidence

        # Collect unique evidence snippets
        unique_snippets: list[str] = []
        seen_snippets: set[str] = set()
        for item in group:
            snippet = item.evidence.strip()
            # Normalize whitespace for comparison
            snippet_key = " ".join(snippet.lower().split())
            if snippet_key and snippet_key not in seen_snippets:
                seen_snippets.add(snippet_key)
                unique_snippets.append(snippet)
                if len(unique_snippets) >= max_evidence_snippets:
                    break

        merged_evidence = " | ".join(unique_snippets)

        merged.append(
            SkillExtractionItem(
                name=best_name,
                category=best_category,
                evidence=merged_evidence,
                confidence=highest_confidence,
            )
        )

    # Sort final list by confidence descending, then name ascending
    merged.sort(key=lambda s: (-s.confidence, s.name.lower()))
    return merged
