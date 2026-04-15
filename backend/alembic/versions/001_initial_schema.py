"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "monthly_closings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("year", "month", name="uq_monthly_closings_year_month"),
    )

    op.create_table(
        "teachers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "siguefit_import_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("closing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_from", sa.Date(), nullable=True),
        sa.Column("source_to", sa.Date(), nullable=True),
        sa.Column("activity_filter", sa.String(length=255), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("uploaded_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["closing_id"], ["monthly_closings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_siguefit_batch_closing_sha",
        "siguefit_import_batches",
        ["closing_id", "file_sha256"],
        unique=True,
    )

    op.create_table(
        "imported_payment_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("closing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.Column("client_name", sa.String(length=512), nullable=True),
        sa.Column("dni", sa.String(length=64), nullable=True),
        sa.Column("payment_category", sa.String(length=512), nullable=False),
        sa.Column("payment_method", sa.String(length=512), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=16), nullable=True),
        sa.Column("activity", sa.Text(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registered_by_user", sa.String(length=255), nullable=True),
        sa.Column("raw_row", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["siguefit_import_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["closing_id"], ["monthly_closings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_imported_payment_lines_closing_id"), "imported_payment_lines", ["closing_id"])
    op.create_index(op.f("ix_imported_payment_lines_batch_id"), "imported_payment_lines", ["batch_id"])

    op.create_table(
        "manual_expenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("closing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expense_type", sa.String(length=32), nullable=False),
        sa.Column("vendor_or_teacher_name", sa.String(length=255), nullable=True),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("hours", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("hourly_rate", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["closing_id"], ["monthly_closings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["teacher_id"], ["teachers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_manual_expenses_closing_id"), "manual_expenses", ["closing_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_manual_expenses_closing_id"), table_name="manual_expenses")
    op.drop_table("manual_expenses")
    op.drop_index(op.f("ix_imported_payment_lines_batch_id"), table_name="imported_payment_lines")
    op.drop_index(op.f("ix_imported_payment_lines_closing_id"), table_name="imported_payment_lines")
    op.drop_table("imported_payment_lines")
    op.drop_index("ix_siguefit_batch_closing_sha", table_name="siguefit_import_batches")
    op.drop_table("siguefit_import_batches")
    op.drop_table("teachers")
    op.drop_table("monthly_closings")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
