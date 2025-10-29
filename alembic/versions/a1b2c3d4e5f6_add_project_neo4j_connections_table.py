"""add project_neo4j_connections table

Revision ID: a1b2c3d4e5f6
Revises: 07c7ae795a24
Create Date: 2025-10-28 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "07c7ae795a24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_neo4j_connections",
        sa.Column("id", sa.String(length=12), nullable=False),
        sa.Column("project_id", sa.String(length=12), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("connection_uri", sa.Text(), nullable=False),
        sa.Column("connection_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("last_error_text", sa.Text(), nullable=True),
        sa.Column("last_error_timestamp", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("soft_deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["user_mundiai_projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("project_neo4j_connections")
