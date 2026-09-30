import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SyllabusBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    department: str | None = Field(default=None, max_length=255)


class SyllabusListItem(SyllabusBase):
    id: uuid.UUID
    institution_id: uuid.UUID | None
    uploaded_by: uuid.UUID | None
    filename: str
    status: str
    error_message: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SyllabusRead(SyllabusListItem):
    raw_text: str

    model_config = ConfigDict(from_attributes=True)


class SyllabusSkillRead(BaseModel):
    skill_id: uuid.UUID
    canonical_name: str
    category: str | None = None
    aliases: list[str] = Field(default_factory=list)
    evidence: str | None = None
    confidence: float = 1.0

    model_config = ConfigDict(from_attributes=True)


class SyllabusSkillsResponse(BaseModel):
    syllabus_id: uuid.UUID
    status: str
    error_message: str | None = None
    skills: list[SyllabusSkillRead] = Field(default_factory=list)
    total: int = 0

    model_config = ConfigDict(from_attributes=True)
