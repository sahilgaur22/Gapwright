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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SyllabusRead(SyllabusListItem):
    raw_text: str

    model_config = ConfigDict(from_attributes=True)
