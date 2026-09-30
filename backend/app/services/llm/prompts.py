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
