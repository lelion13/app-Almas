"""marketing GBP oauth + reviews + telegram reply sessions

Revision ID: 018
Revises: 017
Create Date: 2026-10-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gbp_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("google_account_email", sa.String(255), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=False),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("token_last4", sa.String(4), nullable=False, server_default=""),
        sa.Column("scopes", sa.Text(), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "gbp_oauth_states",
        sa.Column("state", sa.String(128), primary_key=True, nullable=False),
        sa.Column("code_verifier", sa.String(128), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "gbp_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("google_review_id", sa.String(512), nullable=False),
        sa.Column("google_review_name", sa.String(1024), nullable=True),
        sa.Column("star_rating", sa.Integer(), nullable=False),
        sa.Column("reviewer_name", sa.String(255), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("review_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reply_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("reply_text", sa.Text(), nullable=True),
        sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("telegram_message_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("google_review_id", name="uq_gbp_reviews_google_review_id"),
    )
    op.create_index("ix_gbp_reviews_google_review_id", "gbp_reviews", ["google_review_id"])
    op.create_table(
        "gbp_reply_sessions",
        sa.Column("telegram_user_id", sa.String(64), primary_key=True, nullable=False),
        sa.Column("review_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("gbp_reviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("gbp_reply_sessions")
    op.drop_index("ix_gbp_reviews_google_review_id", table_name="gbp_reviews")
    op.drop_table("gbp_reviews")
    op.drop_table("gbp_oauth_states")
    op.drop_table("gbp_connections")
