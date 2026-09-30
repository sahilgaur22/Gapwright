"""add is_expired column to job_postings
Revision ID: 0004_add_job_posting_is_expired
Revises: 0003_add_syllabus_error_message
Create Date: 2026-09-30 12:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_add_job_posting_is_expired"
down_revision: str | None = "0003_add_syllabus_error_message"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "job_postings",
        sa.Column(
            "is_expired",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index("ix_job_postings_is_expired", "job_postings", ["is_expired"])


def downgrade() -> None:
    op.drop_index("ix_job_postings_is_expired", table_name="job_postings")
    op.drop_column("job_postings", "is_expired")
