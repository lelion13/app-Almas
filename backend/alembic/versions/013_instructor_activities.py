"""instructor ↔ activities many-to-many

Revision ID: 013
Revises: 012
Create Date: 2026-09-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "studio_instructor_activities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "instructor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("studio_instructors.id"),
            nullable=False,
        ),
        sa.Column(
            "activity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("studio_activities.id"),
            nullable=False,
        ),
        sa.UniqueConstraint("instructor_id", "activity_id", name="uq_studio_instructor_activity"),
    )
    op.create_index(
        "ix_studio_instructor_activities_instructor_id",
        "studio_instructor_activities",
        ["instructor_id"],
    )
    op.create_index(
        "ix_studio_instructor_activities_activity_id",
        "studio_instructor_activities",
        ["activity_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_studio_instructor_activities_activity_id", table_name="studio_instructor_activities")
    op.drop_index("ix_studio_instructor_activities_instructor_id", table_name="studio_instructor_activities")
    op.drop_table("studio_instructor_activities")
