import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.skill import Skill


class JobSource(Base):
    __tablename__ = "job_sources"

    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    attribution_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attribution_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    may_display_listing: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    postings: Mapped[list["JobPosting"]] = relationship(
        "JobPosting", back_populates="job_source", cascade="all, delete-orphan"
    )
    crawl_states: Mapped[list["CrawlState"]] = relationship(
        "CrawlState", back_populates="job_source", cascade="all, delete-orphan"
    )
    usage_records: Mapped[list["ApiUsage"]] = relationship(
        "ApiUsage", back_populates="job_source", cascade="all, delete-orphan"
    )


class JobPosting(Base):
    __tablename__ = "job_postings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("job_sources.name", ondelete="CASCADE"),
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    description_is_truncated: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    job_source: Mapped[JobSource] = relationship("JobSource", back_populates="postings")
    skills: Mapped[list["JobSkill"]] = relationship(
        "JobSkill", back_populates="job_posting", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "source", "external_id", name="uq_job_postings_source_external_id"
        ),
        Index("ix_job_postings_posted_at", "posted_at"),
        Index("ix_job_postings_last_seen_at", "last_seen_at"),
    )


class CrawlState(Base):
    __tablename__ = "crawl_state"

    source: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("job_sources.name", ondelete="CASCADE"),
        primary_key=True,
    )
    role_query: Mapped[str] = mapped_column(String(255), primary_key=True)
    location: Mapped[str] = mapped_column(String(255), primary_key=True)
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    newest_posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cursor: Mapped[str | None] = mapped_column(String(255), nullable=True)

    job_source: Mapped[JobSource] = relationship(
        "JobSource", back_populates="crawl_states"
    )


class ApiUsage(Base):
    __tablename__ = "api_usage"

    source: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("job_sources.name", ondelete="CASCADE"),
        primary_key=True,
    )
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    calls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    job_source: Mapped[JobSource] = relationship(
        "JobSource", back_populates="usage_records"
    )


class JobSkill(Base):
    __tablename__ = "job_skills"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        primary_key=True,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True,
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    job_posting: Mapped[JobPosting] = relationship(
        "JobPosting", back_populates="skills"
    )
    skill: Mapped["Skill"] = relationship("Skill", back_populates="job_associations")


class SkillDemandDaily(Base):
    __tablename__ = "skill_demand_daily"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    day: Mapped[date] = mapped_column(Date, nullable=False)
    role_query: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
    )
    postings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    demand_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    skill: Mapped["Skill"] = relationship("Skill")

    __table_args__ = (
        UniqueConstraint(
            "day",
            "role_query",
            "location",
            "skill_id",
            name="uq_skill_demand_daily",
        ),
        Index("ix_skill_demand_daily_day", "day"),
        Index("ix_skill_demand_daily_lookup", "role_query", "location", "skill_id"),
    )
