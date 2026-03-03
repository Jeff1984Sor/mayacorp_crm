"""add is_active to addons

Revision ID: 20260303_0006
Revises: 20260303_0005
Create Date: 2026-03-03 00:40:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260303_0006"
down_revision = "20260303_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("addons", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.alter_column("addons", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_column("addons", "is_active")
