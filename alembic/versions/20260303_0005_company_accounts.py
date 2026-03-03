"""add company accounts

Revision ID: 20260303_0005
Revises: 20260301_0004
Create Date: 2026-03-03 09:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260303_0005"
down_revision = "20260301_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("lifecycle_stage", sa.String(length=40), nullable=False, server_default="lead"),
        sa.Column("admin_email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("company_document", sa.String(length=40), nullable=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column("last_converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_company_accounts_name", "company_accounts", ["name"])
    op.create_index("ix_company_accounts_lifecycle_stage", "company_accounts", ["lifecycle_stage"])
    op.create_index("ix_company_accounts_admin_email", "company_accounts", ["admin_email"])


def downgrade() -> None:
    op.drop_index("ix_company_accounts_admin_email", table_name="company_accounts")
    op.drop_index("ix_company_accounts_lifecycle_stage", table_name="company_accounts")
    op.drop_index("ix_company_accounts_name", table_name="company_accounts")
    op.drop_table("company_accounts")

