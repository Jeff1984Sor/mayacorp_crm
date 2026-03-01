from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import DATA_DIR, settings
from app.core.security import hash_password
from app.db.base import TenantBase
from app.db.session import build_tenant_engine
from app.models.central import CentralAuditLog, SaasInvoice, Tenant, TenantSubscription
from app.models.tenant import BankAccount, User
from app.schemas.tenant import TenantCreateRequest
from app.services.tenant_schema import migrate_tenant_schema


def _build_tenant_db_url(slug: str) -> str:
    if settings.central_database_url.startswith("sqlite"):
        tenant_path = Path(DATA_DIR / f"{slug}.db")
        return f"sqlite+pysqlite:///{tenant_path.as_posix()}"

    from sqlalchemy.engine.url import make_url

    central_url = make_url(settings.central_database_url)
    tenant_db_name = f"tenant_{slug}"
    admin_engine = create_engine(central_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.exec_driver_sql(f'CREATE DATABASE "{tenant_db_name}"')
    return str(central_url.set(database=tenant_db_name))


def create_tenant(session: Session, payload: TenantCreateRequest, actor_email: str) -> Tenant:
    tenant_db_url = _build_tenant_db_url(payload.workspace_slug)
    tenant = Tenant(
        name=payload.company_name,
        slug=payload.workspace_slug,
        company_document=payload.company_document,
        admin_email=payload.admin_email,
        plan_code=payload.plan_code,
        billing_day=payload.billing_day,
        discount_percent=payload.discount_percent,
        database_url=tenant_db_url,
    )
    session.add(tenant)
    session.flush()

    tenant_engine = build_tenant_engine(tenant_db_url)
    TenantBase.metadata.create_all(bind=tenant_engine, checkfirst=True)
    migrate_tenant_schema(tenant_engine)

    with Session(tenant_engine) as tenant_session:
        tenant_session.add(
            User(
                email=payload.admin_email,
                full_name=payload.admin_name,
                password_hash=hash_password(payload.admin_password),
                is_admin=True,
                must_change_password=True,
            )
        )
        tenant_session.add(
            BankAccount(
                name="Conta Principal",
                bank_name="Banco Padrão",
                currency="BRL",
                is_default=True,
            )
        )
        tenant_session.commit()

    session.add(
        TenantSubscription(
            tenant_id=tenant.id,
            plan_code=payload.plan_code,
            started_on=date.today(),
            discount_percent=payload.discount_percent,
            status="active",
        )
    )

    if payload.generate_invoice:
        session.add(
            SaasInvoice(
                tenant_id=tenant.id,
                amount=0,
                due_date=date.today(),
                status="pending",
                external_reference="bootstrap",
            )
        )

    session.add(
        CentralAuditLog(
            actor_email=actor_email,
            action="tenant.created",
            target_type="tenant",
            target_id=str(tenant.id),
            payload={
                "slug": payload.workspace_slug,
                "plan_code": payload.plan_code,
                "issue_fiscal_document": payload.issue_fiscal_document,
            },
        )
    )
    session.commit()
    session.refresh(tenant)
    return tenant
