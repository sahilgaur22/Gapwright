"""Versioned prompts for LLM operations in Gapwright."""

PROMPT_VERSION_SKILL_EXTRACTION = "v1.0.0"
PROMPT_VERSION_SKILL_REPAIR = "v1.0.0"

SYSTEM_INSTRUCTION_SKILL_EXTRACTION = (
    "You are an expert curriculum and technical job market analyst. "
    "Your task is to identify and extract concrete, technical, and domain-specific "
    "skills, frameworks, libraries, tools, database systems, platforms, and core "
    "conceptual topics from the provided document text.\n\n"
    "Guidelines:\n"
    "1. Extract specific skills (e.g. 'PostgreSQL', 'Docker', 'Dynamic Programming', "
    "'FastAPI', 'Kubernetes', 'PyTorch'). Avoid generic buzzwords like "
    "'problem solving' or 'good communication'.\n"
    "2. For each skill, assign an appropriate technical category (e.g. 'Languages', "
    "'Frameworks', 'Databases', 'Cloud & DevOps', 'Machine Learning', "
    "'Data Engineering', 'Systems & Architecture', 'Theory & Algorithms').\n"
    "3. Quote the exact evidence phrase or sentence from the document where the "
    "skill is taught or referenced.\n"
    "4. Assign a confidence score between 0.0 and 1.0 reflecting how explicitly "
    "the skill is taught.\n"
    "5. Return your output STRICTLY as valid JSON adhering to this schema:\n"
    '{"skills": [{"name": "Skill Name", "category": "Category", '
    '"evidence": "quote", "confidence": 0.95}]}'
)

SKILL_EXTRACTION_USER_TEMPLATE = (
    "Extract all relevant technical skills and concepts from the following text:\n\n"
    "```\n{text}\n```\n\n"
    "Output valid JSON matching the schema."
)

SYSTEM_INSTRUCTION_SKILL_REPAIR = (
    "You are a strict JSON repair specialist. You receive an invalid or schema-failing "
    "LLM output along with specific validation errors. Your job is to correct the "
    "structure, ensure all required fields ('name', 'category', 'evidence', "
    "'confidence') are present with proper types, and output ONLY valid JSON "
    "matching the schema:\n"
    '{"skills": [{"name": "Skill Name", "category": "Category", '
    '"evidence": "quote", "confidence": 0.95}]}'
)

SKILL_REPAIR_USER_TEMPLATE = (
    "The previous extraction failed schema validation with these errors:\n\n"
    "Validation Errors:\n{errors}\n\n"
    "Malformed Output:\n```json\n{raw_output}\n```\n\n"
    "Please repair and return strictly valid JSON matching the required schema."
)

PROMPT_VERSION_RECOMMENDATIONS = "v1.0.0"

SYSTEM_INSTRUCTION_RECOMMENDATIONS = (
    "You are an academic curriculum design advisor. Based ONLY on empirical job "
    "market demand data provided, provide actionable curriculum adjustment "
    "recommendations.\n\n"
    "Guidelines:\n"
    "1. For skills to ADD: Explain why this skill is needed based on the provided "
    "demand %, suggest a concise academic module title, and recommend teaching "
    "duration in weeks (1-4 weeks).\n"
    "2. For skills to DROP: Explain why this topic is obsolete or unaligned with "
    "market demand and should be phased out.\n"
    "3. Keep all rationales succinct, factual, and strictly grounded in the "
    "provided numbers.\n"
    "4. Return output STRICTLY as valid JSON matching this schema:\n"
    "{\n"
    '  "skills_to_add": [\n'
    '    {"name": "Skill Name", "rationale": "...", "suggested_module": "...", '
    '"suggested_weeks": 2}\n'
    "  ],\n"
    '  "skills_to_drop": [\n'
    '    {"name": "Skill Name", "rationale": "..."}\n'
    "  ],\n"
    '  "summary": "Executive summary of curriculum recommendations."\n'
    "}"
)

RECOMMENDATIONS_USER_TEMPLATE = (
    "Curriculum: {course_title}\n"
    "Target Role: {role_query} in {location}\n"
    "Curriculum Gap: {gap_pct}% (Coverage: {coverage_pct}%)\n\n"
    "Missing Skills with Market Demand:\n{missing_skills_info}\n\n"
    "Syllabus Skills with Low / Zero Market Demand:\n{obsolete_skills_info}\n\n"
    "Generate grounded curriculum recommendations in valid JSON matching the schema."
)
