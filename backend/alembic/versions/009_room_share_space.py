"""room optional shared-space peer (same site)

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
    op.add_column(
        "studio_rooms",
        sa.Column(
            "shares_space_with_room_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("studio_rooms.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_studio_rooms_shares_space_with_room_id", "studio_rooms", ["shares_space_with_room_id"])


def downgrade() -> None:
    op.drop_index("ix_studio_rooms_shares_space_with_room_id", table_name="studio_rooms")
    op.drop_column("studio_rooms", "shares_space_with_room_id")
