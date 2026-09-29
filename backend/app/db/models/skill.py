import uuid
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Index, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.job import JobSkill
    from app.db.models.syllabus import SyllabusSkill


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    canonical_name: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    embedding: Mapped[Any | None] = mapped_column(
        Vector(settings.EMBED_DIM), nullable=True
    )
    aliases: Mapped[list[str]] = mapped_column(
        ARRAY(String).with_variant(JSON, "sqlite"), default=list
    )

    syllabus_associations: Mapped[list["SyllabusSkill"]] = relationship(
        "SyllabusSkill", back_populates="skill", cascade="all, delete-orphan"
    )
    job_associations: Mapped[list["JobSkill"]] = relationship(
        "JobSkill", back_populates="skill", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index(
            "ix_skills_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
