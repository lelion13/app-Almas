"""allow multiple open ranges per room weekday

Revision ID: 008
Revises: 007
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_studio_room_hours_room_weekday", "studio_room_hours", type_="unique")
    op.execute(
        "DELETE FROM studio_room_hours "
        "WHERE is_open IS FALSE OR open_time IS NULL OR close_time IS NULL"
    )
    op.alter_column(
        "studio_room_hours",
        "open_time",
        existing_type=sa.Time(),
        nullable=False,
    )
    op.alter_column(
        "studio_room_hours",
        "close_time",
        existing_type=sa.Time(),
        nullable=False,
    )
    op.drop_column("studio_room_hours", "is_open")
    op.create_index(
        "ix_studio_room_hours_room_weekday",
        "studio_room_hours",
        ["room_id", "weekday"],
    )


def downgrade() -> None:
    op.drop_index("ix_studio_room_hours_room_weekday", table_name="studio_room_hours")
    op.add_column(
        "studio_room_hours",
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.alter_column(
        "studio_room_hours",
        "open_time",
        existing_type=sa.Time(),
        nullable=True,
    )
    op.alter_column(
        "studio_room_hours",
        "close_time",
        existing_type=sa.Time(),
        nullable=True,
    )
    # Collapse to one row per room+weekday (keep earliest open).
    op.execute(
        """
        DELETE FROM studio_room_hours a
        USING studio_room_hours b
        WHERE a.room_id = b.room_id
          AND a.weekday = b.weekday
          AND a.open_time > b.open_time
        """
    )
    op.create_unique_constraint(
        "uq_studio_room_hours_room_weekday",
        "studio_room_hours",
        ["room_id", "weekday"],
    )
