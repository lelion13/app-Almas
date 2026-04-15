"""expense import batches and lines

Revision ID: 002
Revises: 001
Create Date: 2026-04-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "expense_import_batches",
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
        "ix_expense_import_batch_closing_sha",
        "expense_import_batches",
        ["closing_id", "file_sha256"],
        unique=True,
    )

    op.create_table(
        "imported_expense_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("closing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_method", sa.String(length=512), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("raw_row", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["expense_import_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["closing_id"], ["monthly_closings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_imported_expense_lines_closing_id"), "imported_expense_lines", ["closing_id"])
    op.create_index(op.f("ix_imported_expense_lines_batch_id"), "imported_expense_lines", ["batch_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_imported_expense_lines_batch_id"), table_name="imported_expense_lines")
    op.drop_index(op.f("ix_imported_expense_lines_closing_id"), table_name="imported_expense_lines")
    op.drop_table("imported_expense_lines")
    op.drop_index("ix_expense_import_batch_closing_sha", table_name="expense_import_batches")
    op.drop_table("expense_import_batches")
