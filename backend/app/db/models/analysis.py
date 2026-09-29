import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.skill import Skill
    from app.db.models.syllabus import Syllabus


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    syllabus_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("syllabi.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_query: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    gap_pct: Mapped[float] = mapped_column(Float, nullable=False)
    coverage_pct: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    syllabus: Mapped["Syllabus"] = relationship("Syllabus", back_populates="analyses")
    items: Mapped[list["AnalysisItem"]] = relationship(
        "AnalysisItem", back_populates="analysis", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_analyses_syllabus_id", "syllabus_id"),
        Index("ix_analyses_role_location", "role_query", "location"),
    )


class AnalysisItem(Base):
    __tablename__ = "analysis_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # covered, missing, obsolete
    demand_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    demand_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    analysis: Mapped[Analysis] = relationship("Analysis", back_populates="items")
    skill: Mapped["Skill"] = relationship("Skill")

    __table_args__ = (
        Index("ix_analysis_items_analysis_id", "analysis_id"),
        Index("ix_analysis_items_kind", "kind"),
    )
