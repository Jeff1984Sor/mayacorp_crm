"""add tenant analytics snapshots

Revision ID: 20260301_0003
Revises: 20260301_0002
Create Date: 2026-03-01 00:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260301_0003"
down_revision = "20260301_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_analytics_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("period_type", sa.String(length=20), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("tenant_analytics_snapshots")
