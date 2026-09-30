import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JobSkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_id: uuid.UUID
    canonical_name: str
    category: str | None = None
    confidence: float = 1.0


class JobPostingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    external_id: str
    title: str
    company: str | None = None
    location: str | None = None
    description: str
    description_is_truncated: bool = False
    url: str | None = None
    posted_at: datetime | None = None
    scraped_at: datetime
    last_seen_at: datetime
    is_expired: bool = False
    skills: list[str] = Field(default_factory=list)


class JobSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    priority: int
    enabled: bool
    attribution_text: str | None = None
    attribution_url: str | None = None
    may_display_listing: bool = True
    daily_budget: int = 50
    daily_calls_used: int = 0
    remaining_budget: int = 50
    last_run_at: datetime | None = None


class JobPostingsPage(BaseModel):
    items: list[JobPostingRead]
    total: int
    page: int
    page_size: int
    pages: int


class PersistenceResult(BaseModel):
    created_count: int = 0
    updated_count: int = 0
    duplicate_count: int = 0
    skipped_llm_count: int = 0
    extracted_skills_count: int = 0


class CrawlPairRequest(BaseModel):
    role: str
    location: str


class CrawlTriggerRequest(BaseModel):
    pairs: list[CrawlPairRequest] | None = None
    sources: list[str] | None = None
    extract_skills: bool = True


class CrawlTriggerResponse(BaseModel):
    status: str
    pairs_processed: int
    sources_crawled: int
    jobs_persisted: int
    expired_count: int
    snapshot_records_created: int


class SkillDemandItem(BaseModel):
    skill_id: uuid.UUID
    name: str
    category: str | None = None
    postings_count: int
    demand_pct: float
    trend_pct: float = 0.0


class TopSkillsResponse(BaseModel):
    role_query: str
    location: str | None = None
    total_postings: int
    analysis_window_days: int
    trend_window_days: int
    skills: list[SkillDemandItem]
