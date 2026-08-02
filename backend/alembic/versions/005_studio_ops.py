"""studio ops MVP tables

Revision ID: 005
Revises: 004
Create Date: 2026-08-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "studio_sites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.String(512), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "studio_rooms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_sites.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "studio_activities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("level", sa.String(32), nullable=False, server_default="inicial"),
        sa.Column("default_duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "studio_instructors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(64), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "studio_students",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(64), nullable=True),
        sa.Column("document_id", sa.String(64), nullable=True),
        sa.Column("emergency_contact", sa.String(255), nullable=True),
        sa.Column("emergency_phone", sa.String(64), nullable=True),
        sa.Column("medical_notes", sa.Text(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "studio_class_series",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_sites.id"), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_rooms.id"), nullable=False),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_activities.id"), nullable=False),
        sa.Column("instructor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_instructors.id"), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(32), nullable=False, server_default="inicial"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "studio_class_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("series_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_class_series.id"), nullable=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_sites.id"), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_rooms.id"), nullable=False),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_activities.id"), nullable=False),
        sa.Column("instructor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_instructors.id"), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(32), nullable=False, server_default="inicial"),
        sa.Column("status", sa.String(32), nullable=False, server_default="scheduled"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("series_id", "session_date", name="uq_studio_session_series_date"),
    )
    op.create_table(
        "studio_holidays",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_sites.id"), nullable=True),
        sa.Column("holiday_date", sa.Date(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "studio_pack_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("class_count", sa.Integer(), nullable=False),
        sa.Column("validity_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("is_trial", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "studio_student_packs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_students.id"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_pack_products.id"), nullable=False),
        sa.Column("remaining_credits", sa.Integer(), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("expires_on", sa.Date(), nullable=False),
        sa.Column("scope", sa.String(32), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_sites.id"), nullable=True),
        sa.Column("payment_method", sa.String(32), nullable=False, server_default="efectivo"),
        sa.Column("payment_status", sa.String(32), nullable=False, server_default="pagado"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "studio_fixed_enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_students.id"), nullable=False),
        sa.Column("series_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_class_series.id"), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_student_packs.id"), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("student_id", "series_id", name="uq_studio_fixed_enrollment"),
    )
    op.create_table(
        "studio_bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_students.id"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_class_sessions.id"), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_student_packs.id"), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="mobile"),
        sa.Column("status", sa.String(32), nullable=False, server_default="booked"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("student_id", "session_id", name="uq_studio_booking_student_session"),
    )
    op.create_table(
        "studio_waitlist_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_students.id"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_class_sessions.id"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("student_id", "session_id", name="uq_studio_waitlist_student_session"),
    )
    op.create_table(
        "studio_attendance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_bookings.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("noted_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("booking_id", name="uq_studio_attendance_booking"),
    )
    op.create_table(
        "studio_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("no_show_deducts_credit", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("expand_weeks_ahead", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.execute("INSERT INTO studio_settings (id, no_show_deducts_credit, expand_weeks_ahead) VALUES (1, true, 8)")
    op.create_table(
        "studio_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=True),
        sa.Column("summary", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    for t in [
        "studio_audit_logs",
        "studio_settings",
        "studio_attendance",
        "studio_waitlist_entries",
        "studio_bookings",
        "studio_fixed_enrollments",
        "studio_student_packs",
        "studio_pack_products",
        "studio_holidays",
        "studio_class_sessions",
        "studio_class_series",
        "studio_students",
        "studio_instructors",
        "studio_activities",
        "studio_rooms",
        "studio_sites",
    ]:
        op.drop_table(t)
