import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.syllabus import Syllabus


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)

    users: Mapped[list["User"]] = relationship(
        "User", back_populates="institution", cascade="all, delete-orphan"
    )
    syllabi: Mapped[list["Syllabus"]] = relationship(
        "Syllabus", back_populates="institution"
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(50), default="student", nullable=False
    )  # admin, educator, student, policymaker
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    institution: Mapped[Institution | None] = relationship(
        "Institution", back_populates="users"
    )
    uploaded_syllabi: Mapped[list["Syllabus"]] = relationship(
        "Syllabus", back_populates="uploader"
    )

    __table_args__ = (Index("ix_users_role", "role"),)
