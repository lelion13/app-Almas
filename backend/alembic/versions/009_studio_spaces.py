"""physical spaces shared by rooms

Revision ID: 009
Revises: 008
Create Date: 2026-08-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "studio_spaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_sites.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_studio_spaces_site_id", "studio_spaces", ["site_id"])
    op.add_column(
        "studio_rooms",
        sa.Column("space_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_spaces.id"), nullable=True),
    )
    op.create_index("ix_studio_rooms_space_id", "studio_rooms", ["space_id"])


def downgrade() -> None:
    op.drop_index("ix_studio_rooms_space_id", table_name="studio_rooms")
    op.drop_column("studio_rooms", "space_id")
    op.drop_index("ix_studio_spaces_site_id", table_name="studio_spaces")
    op.drop_table("studio_spaces")
