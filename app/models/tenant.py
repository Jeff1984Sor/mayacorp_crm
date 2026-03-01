from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TenantBase


def utcnow() -> datetime:
    return datetime.now(UTC)


class TenantTimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class User(TenantTimestampMixin, TenantBase):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[str] = mapped_column(String(40), default="admin")
    permissions: Mapped[dict] = mapped_column(JSON, default=dict)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)


class TenantRefreshToken(TenantTimestampMixin, TenantBase):
    __tablename__ = "tenant_refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_email: Mapped[str] = mapped_column(String(255), index=True)
    token_jti: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TenantSchemaVersion(TenantTimestampMixin, TenantBase):
    __tablename__ = "tenant_schema_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(40), unique=True, index=True)


class Lead(TenantTimestampMixin, TenantBase):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(40))
    source: Mapped[str | None] = mapped_column(String(80))
    manual_classification: Mapped[str | None] = mapped_column(String(80))
    conversion_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)


class Client(TenantTimestampMixin, TenantBase):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(40))
    source_lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"))


class Message(TenantTimestampMixin, TenantBase):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"))
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"))
    direction: Mapped[str] = mapped_column(String(20), default="outbound")
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="sending")


class TenantWhatsappAccount(TenantTimestampMixin, TenantBase):
    __tablename__ = "tenant_whatsapp_account"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_session_id: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(40), default="disconnected")
    last_qr_code: Mapped[str | None] = mapped_column(Text)


class SalesOrder(TenantTimestampMixin, TenantBase):
    __tablename__ = "sales_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"))
    order_type: Mapped[str] = mapped_column(String(20), default="one_time")
    duration_months: Mapped[int | None] = mapped_column(Integer)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[str] = mapped_column(String(40), default="draft")


class SalesItem(TenantTimestampMixin, TenantBase):
    __tablename__ = "sales_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    sales_order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"))
    description: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[float] = mapped_column(Numeric(12, 2), default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)


class AccountsReceivable(TenantTimestampMixin, TenantBase):
    __tablename__ = "accounts_receivable"

    id: Mapped[int] = mapped_column(primary_key=True)
    sales_order_id: Mapped[int | None] = mapped_column(ForeignKey("sales_orders.id"))
    due_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(40), default="pending")
    category: Mapped[str | None] = mapped_column(String(80))
    cost_center: Mapped[str | None] = mapped_column(String(80))


class AccountsPayable(TenantTimestampMixin, TenantBase):
    __tablename__ = "accounts_payable"

    id: Mapped[int] = mapped_column(primary_key=True)
    due_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(40), default="pending")
    category: Mapped[str | None] = mapped_column(String(80))
    cost_center: Mapped[str | None] = mapped_column(String(80))


class FinanceCategory(TenantTimestampMixin, TenantBase):
    __tablename__ = "finance_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    entry_type: Mapped[str] = mapped_column(String(20), default="both")


class CostCenter(TenantTimestampMixin, TenantBase):
    __tablename__ = "cost_centers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)


class BankAccount(TenantTimestampMixin, TenantBase):
    __tablename__ = "bank_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    bank_name: Mapped[str] = mapped_column(String(120))
    currency: Mapped[str] = mapped_column(String(8), default="BRL")
    is_default: Mapped[bool] = mapped_column(Boolean, default=True)


class Proposal(TenantTimestampMixin, TenantBase):
    __tablename__ = "proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"))
    sales_order_id: Mapped[int | None] = mapped_column(ForeignKey("sales_orders.id"))
    title: Mapped[str] = mapped_column(String(255))
    template_name: Mapped[str | None] = mapped_column(String(120))
    pdf_path: Mapped[str | None] = mapped_column(Text)
    is_sendable: Mapped[bool] = mapped_column(Boolean, default=True)


class Contract(TenantTimestampMixin, TenantBase):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"))
    sales_order_id: Mapped[int | None] = mapped_column(ForeignKey("sales_orders.id"))
    title: Mapped[str] = mapped_column(String(255))
    template_name: Mapped[str | None] = mapped_column(String(120))
    pdf_path: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="draft")
    signed_file_path: Mapped[str | None] = mapped_column(Text)


class MarketplaceEvent(TenantTimestampMixin, TenantBase):
    __tablename__ = "marketplace_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel: Mapped[str] = mapped_column(String(80))
    external_order_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    sales_order_id: Mapped[int | None] = mapped_column(ForeignKey("sales_orders.id"))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class File(TenantTimestampMixin, TenantBase):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[int] = mapped_column(Integer)
    path: Mapped[str] = mapped_column(Text)
    signed_url_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LeadRadarRun(TenantTimestampMixin, TenantBase):
    __tablename__ = "lead_radar_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_run_id: Mapped[str | None] = mapped_column(String(120), unique=True)
    status: Mapped[str] = mapped_column(String(40), default="queued")
    source: Mapped[str] = mapped_column(String(80), default="google_places")
    summary: Mapped[dict] = mapped_column(JSON, default=dict)


class WhatsappUnmatchedInbox(TenantTimestampMixin, TenantBase):
    __tablename__ = "whatsapp_unmatched_inbox"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_sender: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text)
    matched: Mapped[bool] = mapped_column(Boolean, default=False)
