"""model week slots for salon×activity; abono links to slots

Revision ID: 017
Revises: 016
Create Date: 2026-09-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "studio_model_week_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_rooms.id"), nullable=False),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_activities.id"), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("instructor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_instructors.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("room_id", "activity_id", "weekday", "start_time", name="uq_studio_model_week_slot"),
    )
    op.create_table(
        "studio_model_week_students",
        sa.Column(
            "slot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("studio_model_week_slots.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_students.id"), primary_key=True),
    )
    op.create_table(
        "studio_abono_model_slots",
        sa.Column(
            "abono_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("studio_abonos.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "slot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("studio_model_week_slots.id"),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("studio_abono_model_slots")
    op.drop_table("studio_model_week_students")
    op.drop_table("studio_model_week_slots")
