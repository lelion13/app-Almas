"""nullable booking pack_id + align student emails with login

Revision ID: 015
Revises: 014
Create Date: 2026-09-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "studio_bookings",
        "pack_id",
        existing_type=sa.UUID(),
        nullable=True,
    )
    # Login user email is authoritative when a student account is linked.
    op.execute(
        """
        UPDATE studio_students AS ss
        SET email = u.email
        FROM users AS u
        WHERE ss.user_id = u.id
          AND u.email IS NOT NULL
          AND ss.email IS DISTINCT FROM u.email
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM studio_bookings WHERE pack_id IS NULL")
    op.alter_column(
        "studio_bookings",
        "pack_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
