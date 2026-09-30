from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RawJob(BaseModel):
    """Normalized raw job posting payload extracted from a job data source."""

    source: str = Field(
        ..., description="Source identifier, e.g. adzuna, jooble, remotive"
    )
    external_id: str = Field(..., description="Source-unique job identifier")
    title: str = Field(..., min_length=1, description="Job posting title")
    company: str | None = Field(default=None, description="Hiring company name")
    location: str | None = Field(default=None, description="Job location or 'Remote'")
    description: str = Field(..., description="Full text or excerpt of job description")
    description_is_truncated: bool = Field(
        default=False,
        description="True if provider supplies excerpt rather than full description",
    )
    url: str | None = Field(
        default=None, description="Direct URL or redirect link to job listing"
    )
    posted_at: datetime | None = Field(
        default=None, description="Publication timestamp from source"
    )
    attribution_text: str | None = Field(
        default=None, description="Required attribution label for display"
    )
    attribution_url: str | None = Field(
        default=None, description="Required attribution backlink URL"
    )
    may_display_listing: bool = Field(
        default=True,
        description="Whether terms permit displaying listing text in UI",
    )

    model_config = ConfigDict(from_attributes=True)
