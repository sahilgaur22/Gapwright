import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.skill import Skill
    from app.db.models.user import Institution, User


class Syllabus(Base):
    __tablename__ = "syllabi"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=True,
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="uploaded", nullable=False
    )  # uploaded, processing, ready, failed
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    institution: Mapped["Institution | None"] = relationship(
        "Institution", back_populates="syllabi"
    )
    uploader: Mapped["User | None"] = relationship(
        "User", back_populates="uploaded_syllabi"
    )
    skills: Mapped[list["SyllabusSkill"]] = relationship(
        "SyllabusSkill", back_populates="syllabus", cascade="all, delete-orphan"
    )
    analyses: Mapped[list["Analysis"]] = relationship(
        "Analysis", back_populates="syllabus", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_syllabi_status", "status"),
        Index("ix_syllabi_institution_id", "institution_id"),
    )


class SyllabusSkill(Base):
    __tablename__ = "syllabus_skills"

    syllabus_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("syllabi.id", ondelete="CASCADE"),
        primary_key=True,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True,
    )
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    syllabus: Mapped[Syllabus] = relationship("Syllabus", back_populates="skills")
    skill: Mapped["Skill"] = relationship(
        "Skill", back_populates="syllabus_associations"
    )


from app.db.models.analysis import Analysis  # noqa: E402
