from pydantic import BaseModel, ConfigDict, Field


class SkillExtractionItem(BaseModel):
    """Individual skill extracted from syllabus or job document."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Concise name of the technical skill or concept",
    )
    category: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Domain category (e.g. Languages, Frameworks, Cloud, ML)",
    )
    evidence: str = Field(
        ...,
        min_length=1,
        description="Exact quote or phrase from the document referencing this skill",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Extraction confidence score between 0.0 and 1.0",
    )

    model_config = ConfigDict(from_attributes=True)


class SkillExtractionResult(BaseModel):
    """Container for a list of extracted skills from a document chunk."""

    skills: list[SkillExtractionItem] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
