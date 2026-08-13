"""ensure shares_space_with_room_id exists (009 may have been rewritten)

Revision ID: 010
Revises: 009
Create Date: 2026-08-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    room_cols = {col["name"] for col in inspector.get_columns("studio_rooms")}
    room_indexes = {idx["name"] for idx in inspector.get_indexes("studio_rooms")}
    tables = set(inspector.get_table_names())

    if "shares_space_with_room_id" not in room_cols:
        op.add_column(
            "studio_rooms",
            sa.Column(
                "shares_space_with_room_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("studio_rooms.id"),
                nullable=True,
            ),
        )
    if "ix_studio_rooms_shares_space_with_room_id" not in room_indexes:
        op.create_index(
            "ix_studio_rooms_shares_space_with_room_id",
            "studio_rooms",
            ["shares_space_with_room_id"],
        )

    # Abandoned "studio_spaces" design (rewritten 009). Safe if it never existed.
    if "space_id" in room_cols:
        op.execute("ALTER TABLE studio_rooms DROP COLUMN IF EXISTS space_id CASCADE")
    if "studio_spaces" in tables:
        op.execute("DROP TABLE IF EXISTS studio_spaces CASCADE")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    room_indexes = {idx["name"] for idx in inspector.get_indexes("studio_rooms")}
    if "ix_studio_rooms_shares_space_with_room_id" in room_indexes:
        op.drop_index("ix_studio_rooms_shares_space_with_room_id", table_name="studio_rooms")
    room_cols = {col["name"] for col in inspector.get_columns("studio_rooms")}
    if "shares_space_with_room_id" in room_cols:
        op.drop_column("studio_rooms", "shares_space_with_room_id")
