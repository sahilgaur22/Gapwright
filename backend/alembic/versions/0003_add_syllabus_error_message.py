"""add error_message column to syllabi

Revision ID: 0003_add_syllabus_error_message
Revises: 0002_create_core_tables
Create Date: 2026-09-30 09:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_add_syllabus_error_message"
down_revision: str | None = "0002_create_core_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("syllabi", sa.Column("error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("syllabi", "error_message")
