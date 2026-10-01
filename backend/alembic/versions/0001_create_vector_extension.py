"""create vector extension

Revision ID: 0001_create_vector_extension
Revises:
Create Date: 2026-09-29 23:25:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_create_vector_extension"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    available = conn.execute(
        sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
    ).scalar()
    if available:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")


def downgrade() -> None:
    conn = op.get_bind()
    installed = conn.execute(
        sa.text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
    ).scalar()
    if installed:
        op.execute("DROP EXTENSION IF EXISTS vector;")
