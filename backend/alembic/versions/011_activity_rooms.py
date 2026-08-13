"""activity ↔ rooms many-to-many

Revision ID: 011
Revises: 010
Create Date: 2026-08-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "studio_activity_rooms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "activity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("studio_activities.id"),
            nullable=False,
        ),
        sa.Column(
            "room_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("studio_rooms.id"),
            nullable=False,
        ),
        sa.UniqueConstraint("activity_id", "room_id", name="uq_studio_activity_room"),
    )
    op.create_index("ix_studio_activity_rooms_activity_id", "studio_activity_rooms", ["activity_id"])
    op.create_index("ix_studio_activity_rooms_room_id", "studio_activity_rooms", ["room_id"])


def downgrade() -> None:
    op.drop_index("ix_studio_activity_rooms_room_id", table_name="studio_activity_rooms")
    op.drop_index("ix_studio_activity_rooms_activity_id", table_name="studio_activity_rooms")
    op.drop_table("studio_activity_rooms")
