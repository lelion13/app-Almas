"""widen mp_accounts.scopes to text

Revision ID: 004
Revises: 003
Create Date: 2026-07-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "mp_accounts",
        "scopes",
        existing_type=sa.String(length=512),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "mp_accounts",
        "scopes",
        existing_type=sa.Text(),
        type_=sa.String(length=512),
        existing_nullable=True,
    )
