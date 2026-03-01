from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CentralBase


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class CentralUser(TimestampMixin, CentralBase):
    __tablename__ = "central_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Tenant(TimestampMixin, CentralBase):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    company_document: Mapped[str | None] = mapped_column(String(40))
    admin_email: Mapped[str] = mapped_column(String(255))
    plan_code: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), default="active")
    billing_day: Mapped[int] = mapped_column(Integer, default=1)
    discount_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    database_url: Mapped[str] = mapped_column(Text)


class CentralSetting(TimestampMixin, CentralBase):
    __tablename__ = "central_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(120), unique=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)


class CentralJwtKey(TimestampMixin, CentralBase):
    __tablename__ = "central_jwt_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    key_id: Mapped[str] = mapped_column(String(64), unique=True)
    secret: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CentralRefreshToken(TimestampMixin, CentralBase):
    __tablename__ = "central_refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_email: Mapped[str] = mapped_column(String(255), index=True)
    token_jti: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CentralAuditLog(CentralBase):
    __tablename__ = "central_audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    actor_email: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(120))
    target_type: Mapped[str] = mapped_column(String(80))
    target_id: Mapped[str] = mapped_column(String(120))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class Plan(TimestampMixin, CentralBase):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    limits: Mapped[list["PlanLimit"]] = relationship(back_populates="plan", cascade="all, delete-orphan")
    prices: Mapped[list["PlanPrice"]] = relationship(back_populates="plan", cascade="all, delete-orphan")


class PlanLimit(TimestampMixin, CentralBase):
    __tablename__ = "plan_limits"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    metric: Mapped[str] = mapped_column(String(120))
    limit_value: Mapped[int] = mapped_column(Integer)
    plan: Mapped["Plan"] = relationship(back_populates="limits")


class PlanPrice(TimestampMixin, CentralBase):
    __tablename__ = "plan_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    billing_cycle: Mapped[str] = mapped_column(String(40))
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(8), default="BRL")
    plan: Mapped["Plan"] = relationship(back_populates="prices")


class Addon(TimestampMixin, CentralBase):
    __tablename__ = "addons"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)


class PlanAddon(TimestampMixin, CentralBase):
    __tablename__ = "plan_addons"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    addon_id: Mapped[int] = mapped_column(ForeignKey("addons.id"))


class TenantSubscription(TimestampMixin, CentralBase):
    __tablename__ = "tenant_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"))
    plan_code: Mapped[str] = mapped_column(String(80))
    started_on: Mapped[Date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), default="active")
    discount_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0)


class SaasInvoice(TimestampMixin, CentralBase):
    __tablename__ = "saas_invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"))
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    due_date: Mapped[Date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), default="pending")
    external_reference: Mapped[str | None] = mapped_column(String(120))


class CentralAiSetting(TimestampMixin, CentralBase):
    __tablename__ = "central_ai_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(80), default="gemini")
    config: Mapped[dict] = mapped_column(JSON, default=dict)


class TenantAiLimit(TimestampMixin, CentralBase):
    __tablename__ = "tenant_ai_limits"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"))
    monthly_request_limit: Mapped[int] = mapped_column(Integer, default=0)
    monthly_token_limit: Mapped[int] = mapped_column(Integer, default=0)


class TenantAiUsageDaily(CentralBase):
    __tablename__ = "tenant_ai_usage_daily"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"))
    usage_date: Mapped[Date] = mapped_column(Date)
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    token_count: Mapped[int] = mapped_column(Integer, default=0)


class TenantHealthScore(TimestampMixin, CentralBase):
    __tablename__ = "tenant_health_score"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"))
    score: Mapped[int] = mapped_column(Integer, default=100)
    status: Mapped[str] = mapped_column(String(40), default="healthy")
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CentralTask(TimestampMixin, CentralBase):
    __tablename__ = "central_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(ForeignKey("tenants.id"))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="open")


class CentralWhatsappSetting(TimestampMixin, CentralBase):
    __tablename__ = "central_whatsapp_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(80), default="wasenderapi")
    config: Mapped[dict] = mapped_column(JSON, default=dict)


class TenantAnalyticsSnapshot(TimestampMixin, CentralBase):
    __tablename__ = "tenant_analytics_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"))
    snapshot_date: Mapped[Date] = mapped_column(Date)
    period_type: Mapped[str] = mapped_column(String(20), default="daily")
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
