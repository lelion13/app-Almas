"""room default duration and weekly open hours

Revision ID: 007
Revises: 006
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "studio_rooms",
        sa.Column("default_class_duration_minutes", sa.Integer(), nullable=True),
    )
    op.execute(
        "UPDATE studio_rooms SET default_class_duration_minutes = 60 "
        "WHERE default_class_duration_minutes IS NULL"
    )
    op.alter_column(
        "studio_rooms",
        "default_class_duration_minutes",
        existing_type=sa.Integer(),
        nullable=False,
        server_default="60",
    )

    op.create_table(
        "studio_room_hours",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_rooms.id"), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("open_time", sa.Time(), nullable=True),
        sa.Column("close_time", sa.Time(), nullable=True),
        sa.UniqueConstraint("room_id", "weekday", name="uq_studio_room_hours_room_weekday"),
    )
    op.create_index("ix_studio_room_hours_room_id", "studio_room_hours", ["room_id"])


def downgrade() -> None:
    op.drop_index("ix_studio_room_hours_room_id", table_name="studio_room_hours")
    op.drop_table("studio_room_hours")
    op.drop_column("studio_rooms", "default_class_duration_minutes")
