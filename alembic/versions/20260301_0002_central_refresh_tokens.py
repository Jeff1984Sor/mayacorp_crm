"""add central refresh tokens

Revision ID: 20260301_0002
Revises: 20260301_0001
Create Date: 2026-03-01 00:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260301_0002"
down_revision = "20260301_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "central_refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_email", sa.String(length=255), nullable=False),
        sa.Column("token_jti", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("token_jti"),
    )
    op.create_index("ix_central_refresh_tokens_user_email", "central_refresh_tokens", ["user_email"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_central_refresh_tokens_user_email", table_name="central_refresh_tokens")
    op.drop_table("central_refresh_tokens")
