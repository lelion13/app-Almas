"""align instructor profile email with linked login user

Revision ID: 014
Revises: 013
Create Date: 2026-09-01
"""

from typing import Sequence, Union

from alembic import op

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Login user email is authoritative when an instructor account is linked.
    op.execute(
        """
        UPDATE studio_instructors AS si
        SET email = u.email
        FROM users AS u
        WHERE si.user_id = u.id
          AND u.email IS NOT NULL
          AND si.email IS DISTINCT FROM u.email
        """
    )


def downgrade() -> None:
    # Data repair only; previous divergent contact emails cannot be restored.
    pass
