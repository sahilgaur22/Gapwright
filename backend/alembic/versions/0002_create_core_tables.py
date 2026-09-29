"""create core tables

Revision ID: 0002_create_core_tables
Revises: 0001_create_vector_extension
Create Date: 2026-09-29 23:28:00.000000

"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "0002_create_core_tables"
down_revision: str | None = "0001_create_vector_extension"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. institutions
    op.create_table(
        "institutions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=True),
    )
    op.create_index("ix_institutions_name", "institutions", ["name"])

    # 2. users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role", sa.String(length=50), nullable=False, server_default="student"
        ),
        sa.Column(
            "institution_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("institutions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])

    # 3. syllabi
    op.create_table(
        "syllabi",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "institution_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("institutions.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "uploaded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="uploaded",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_syllabi_status", "syllabi", ["status"])
    op.create_index("ix_syllabi_institution_id", "syllabi", ["institution_id"])

    # 4. job_sources
    op.create_table(
        "job_sources",
        sa.Column("name", sa.String(length=100), primary_key=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("attribution_text", sa.String(length=255), nullable=True),
        sa.Column("attribution_url", sa.String(length=500), nullable=True),
        sa.Column(
            "may_display_listing",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )

    # 5. job_postings
    op.create_table(
        "job_postings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source",
            sa.String(length=100),
            sa.ForeignKey("job_sources.name", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "description_is_truncated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "source", "external_id", name="uq_job_postings_source_external_id"
        ),
    )
    op.create_index("ix_job_postings_location", "job_postings", ["location"])
    op.create_index("ix_job_postings_posted_at", "job_postings", ["posted_at"])
    op.create_index("ix_job_postings_last_seen_at", "job_postings", ["last_seen_at"])

    # 6. crawl_state
    op.create_table(
        "crawl_state",
        sa.Column(
            "source",
            sa.String(length=100),
            sa.ForeignKey("job_sources.name", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("role_query", sa.String(length=255), primary_key=True),
        sa.Column("location", sa.String(length=255), primary_key=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("newest_posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cursor", sa.String(length=255), nullable=True),
    )

    # 7. api_usage
    op.create_table(
        "api_usage",
        sa.Column(
            "source",
            sa.String(length=100),
            sa.ForeignKey("job_sources.name", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("calls", sa.Integer(), nullable=False, server_default="0"),
    )

    # 8. skills
    op.create_table(
        "skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("canonical_name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column(
            "embedding",
            pgvector.sqlalchemy.Vector(settings.EMBED_DIM),
            nullable=True,
        ),
        sa.Column(
            "aliases",
            postgresql.ARRAY(sa.String()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.create_index(
        "ix_skills_canonical_name", "skills", ["canonical_name"], unique=True
    )
    op.create_index("ix_skills_category", "skills", ["category"])
    op.create_index(
        "ix_skills_embedding_hnsw",
        "skills",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    # 9. syllabus_skills
    op.create_table(
        "syllabus_skills",
        sa.Column(
            "syllabus_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("syllabi.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "skill_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
    )

    # 10. job_skills
    op.create_table(
        "job_skills",
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_postings.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "skill_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
    )

    # 11. skill_demand_daily
    op.create_table(
        "skill_demand_daily",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("role_query", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column(
            "skill_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("postings_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("demand_pct", sa.Float(), nullable=False, server_default="0.0"),
        sa.UniqueConstraint(
            "day",
            "role_query",
            "location",
            "skill_id",
            name="uq_skill_demand_daily",
        ),
    )
    op.create_index("ix_skill_demand_daily_day", "skill_demand_daily", ["day"])
    op.create_index(
        "ix_skill_demand_daily_lookup",
        "skill_demand_daily",
        ["role_query", "location", "skill_id"],
    )

    # 12. analyses
    op.create_table(
        "analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "syllabus_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("syllabi.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role_query", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("gap_pct", sa.Float(), nullable=False),
        sa.Column("coverage_pct", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_analyses_syllabus_id", "analyses", ["syllabus_id"])
    op.create_index("ix_analyses_role_location", "analyses", ["role_query", "location"])

    # 13. analysis_items
    op.create_table(
        "analysis_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "skill_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("demand_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("demand_pct", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("rank", sa.Integer(), nullable=True),
    )
    op.create_index("ix_analysis_items_analysis_id", "analysis_items", ["analysis_id"])
    op.create_index("ix_analysis_items_kind", "analysis_items", ["kind"])


def downgrade() -> None:
    op.drop_table("analysis_items")
    op.drop_table("analyses")
    op.drop_table("skill_demand_daily")
    op.drop_table("job_skills")
    op.drop_table("syllabus_skills")
    op.drop_table("skills")
    op.drop_table("api_usage")
    op.drop_table("crawl_state")
    op.drop_table("job_postings")
    op.drop_table("job_sources")
    op.drop_table("syllabi")
    op.drop_table("users")
    op.drop_table("institutions")
