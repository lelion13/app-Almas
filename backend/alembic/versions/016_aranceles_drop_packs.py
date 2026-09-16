"""drop packs/fixed enrollments; add aranceles and abonos

Revision ID: 016
Revises: 015
Create Date: 2026-09-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("studio_fixed_enrollments")
    op.drop_constraint("studio_bookings_pack_id_fkey", "studio_bookings", type_="foreignkey")
    op.drop_column("studio_bookings", "pack_id")
    op.drop_table("studio_student_packs")
    op.drop_table("studio_pack_products")

    op.create_table(
        "studio_aranceles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("classes_per_week", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "studio_arancel_activities",
        sa.Column(
            "arancel_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("studio_aranceles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "activity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("studio_activities.id"),
            primary_key=True,
        ),
    )
    op.create_table(
        "studio_abonos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_students.id"), nullable=False),
        sa.Column("arancel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_aranceles.id"), nullable=False),
        sa.Column("agreed_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_on", sa.Date(), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("annulled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("annulled_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_studio_abonos_student_id", "studio_abonos", ["student_id"])
    op.create_table(
        "studio_abono_series",
        sa.Column(
            "abono_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("studio_abonos.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "series_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("studio_class_series.id"),
            primary_key=True,
        ),
    )
    op.create_table(
        "studio_abono_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "abono_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("studio_abonos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_on", sa.Date(), nullable=False),
        sa.Column("method", sa.String(32), nullable=False, server_default="efectivo"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.add_column(
        "studio_bookings",
        sa.Column("abono_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_abonos.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_constraint("studio_bookings_abono_id_fkey", "studio_bookings", type_="foreignkey")
    op.drop_column("studio_bookings", "abono_id")
    op.drop_table("studio_abono_payments")
    op.drop_table("studio_abono_series")
    op.drop_index("ix_studio_abonos_student_id", table_name="studio_abonos")
    op.drop_table("studio_abonos")
    op.drop_table("studio_arancel_activities")
    op.drop_table("studio_aranceles")

    op.create_table(
        "studio_pack_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
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
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
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
    op.add_column(
        "studio_bookings",
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_student_packs.id"), nullable=True),
    )
    op.create_table(
        "studio_fixed_enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_students.id"), nullable=False),
        sa.Column("series_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_class_series.id"), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_student_packs.id"), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("student_id", "series_id", name="uq_studio_fixed_enrollment"),
    )
