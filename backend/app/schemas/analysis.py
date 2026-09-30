import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class MatchType(StrEnum):
    EXACT = "exact"
    ALIAS = "alias"
    SEMANTIC = "semantic"


class SkillMatchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    syllabus_skill_id: uuid.UUID
    syllabus_skill_name: str
    market_skill_id: uuid.UUID
    market_skill_name: str
    similarity: float = Field(ge=0.0, le=1.0)
    match_type: MatchType


class AnalysisItemKind(StrEnum):
    COVERED = "covered"
    MISSING = "missing"
    OBSOLETE = "obsolete"


class AnalysisItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_id: uuid.UUID
    skill_name: str
    category: str | None = None
    kind: AnalysisItemKind
    demand_count: int = 0
    demand_pct: float = 0.0
    rank: int = 0
    matched_syllabus_skill: str | None = None
    similarity: float | None = None


class AnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    syllabus_id: uuid.UUID
    role_query: str
    location: str | None = None
    gap_pct: float
    coverage_pct: float
    created_at: datetime
    items: list[AnalysisItemRead] = Field(default_factory=list)


class AnalysisCreateRequest(BaseModel):
    syllabus_id: uuid.UUID
    role_query: str = Field(..., min_length=1)
    location: str | None = None
    remote_only: bool = False


class SkillRecommendationAction(StrEnum):
    ADD = "add"
    DROP = "drop"


class SkillRecommendationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_id: uuid.UUID
    skill_name: str
    category: str | None = None
    action: SkillRecommendationAction
    demand_pct: float
    trend_pct: float = 0.0
    rationale: str
    suggested_module: str = ""
    suggested_weeks: int = 2


class CurriculumRecommendationsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_id: uuid.UUID
    syllabus_id: uuid.UUID
    course_title: str
    role_query: str
    location: str
    gap_pct: float
    coverage_pct: float
    skills_to_add: list[SkillRecommendationItem] = Field(default_factory=list)
    skills_to_drop: list[SkillRecommendationItem] = Field(default_factory=list)
    summary: str

