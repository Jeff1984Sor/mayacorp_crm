from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import DATA_DIR, settings
from app.core.security import hash_password
from app.db.base import TenantBase
from app.db.session import build_tenant_engine
from app.models.central import Addon, CentralAuditLog, CompanyAccount, Plan, PlanPrice, SaasInvoice, Tenant, TenantSubscription
from app.models.tenant import BankAccount, CostCenter, FinanceCategory, RoleTemplate, User
from app.schemas.tenant import TenantCreateRequest
from app.services.tenant_schema import migrate_tenant_schema


def _build_tenant_db_url(slug: str) -> str:
    if settings.central_database_url.startswith("sqlite"):
        tenant_path = Path(DATA_DIR / f"{slug}.db")
        if tenant_path.exists():
            raise ValueError("Workspace database already exists for this slug.")
        return f"sqlite+pysqlite:///{tenant_path.as_posix()}"

    from sqlalchemy.engine.url import make_url

    central_url = make_url(settings.central_database_url)
    tenant_db_name = f"tenant_{slug}"
    admin_engine = create_engine(central_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.exec_driver_sql(
            "SELECT 1 FROM pg_database WHERE datname = %(db_name)s",
            {"db_name": tenant_db_name},
        ).scalar()
        if exists:
            raise ValueError("Workspace database already exists for this slug.")
        conn.exec_driver_sql(f'CREATE DATABASE "{tenant_db_name}"')
    return str(central_url.set(database=tenant_db_name))


def sync_company_account(
    session: Session,
    *,
    account_id: int | None = None,
    company_name: str,
    lifecycle_stage: str,
    admin_email: str,
    company_document: str | None,
    tenant_id: int | None,
    actor_email: str,
) -> CompanyAccount:
    account = None
    if account_id is not None:
        account = session.query(CompanyAccount).filter(CompanyAccount.id == account_id).one_or_none()
    if account is None:
        account = (
            session.query(CompanyAccount)
            .filter(CompanyAccount.admin_email == admin_email, CompanyAccount.name == company_name)
            .order_by(CompanyAccount.id.desc())
            .one_or_none()
        )
    action = "account.updated"
    if account is None:
        account = CompanyAccount(
            name=company_name,
            lifecycle_stage=lifecycle_stage,
            admin_email=admin_email,
            company_document=company_document,
            tenant_id=tenant_id,
            last_converted_at=datetime.now(UTC) if lifecycle_stage == "client" else None,
        )
        session.add(account)
        session.flush()
        action = "account.created"
    else:
        if account.lifecycle_stage != "client" and lifecycle_stage == "client":
            account.last_converted_at = datetime.now(UTC)
        account.name = company_name
        account.lifecycle_stage = lifecycle_stage
        account.admin_email = admin_email
        account.company_document = company_document
        if tenant_id is not None:
            account.tenant_id = tenant_id

    session.add(
        CentralAuditLog(
            actor_email=actor_email,
            action=action,
            target_type="company_account",
            target_id=str(account.id),
            payload={"stage": account.lifecycle_stage, "tenant_id": account.tenant_id},
        )
    )
    session.flush()
    return account


def create_tenant(
    session: Session,
    payload: TenantCreateRequest,
    actor_email: str,
    account_stage: str = "lead",
    account_id: int | None = None,
) -> Tenant:
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
    sync_company_account(
        session,
        account_id=account_id,
        company_name=payload.company_name,
        lifecycle_stage=account_stage,
        admin_email=payload.admin_email,
        company_document=payload.company_document,
        tenant_id=tenant.id,
        actor_email=actor_email,
    )

    tenant_engine = build_tenant_engine(tenant_db_url)
    TenantBase.metadata.create_all(bind=tenant_engine, checkfirst=True)
    migrate_tenant_schema(tenant_engine)

    with Session(tenant_engine) as tenant_session:
        admin_template = tenant_session.query(RoleTemplate).filter(RoleTemplate.role_name == "admin").one_or_none()
        tenant_session.add(
            User(
                email=payload.admin_email,
                full_name=payload.admin_name,
                password_hash=hash_password(payload.admin_password),
                is_admin=True,
                role="admin",
                permissions=admin_template.permissions if admin_template else {},
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
        if tenant_session.query(FinanceCategory).filter(FinanceCategory.name == "Vendas").one_or_none() is None:
            tenant_session.add(FinanceCategory(name="Vendas", entry_type="receivable"))
        if tenant_session.query(FinanceCategory).filter(FinanceCategory.name == "Operacional").one_or_none() is None:
            tenant_session.add(FinanceCategory(name="Operacional", entry_type="payable"))
        if tenant_session.query(CostCenter).filter(CostCenter.name == "Comercial").one_or_none() is None:
            tenant_session.add(CostCenter(name="Comercial"))
        if tenant_session.query(CostCenter).filter(CostCenter.name == "Operacoes").one_or_none() is None:
            tenant_session.add(CostCenter(name="Operacoes"))
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
        plan = session.query(Plan).filter(Plan.code == payload.plan_code).one_or_none()
        plan_price = None
        if plan is not None:
            plan_price = (
                session.query(PlanPrice)
                .filter(PlanPrice.plan_id == plan.id, PlanPrice.billing_cycle == "monthly")
                .one_or_none()
            )
        addon_total = 0.0
        if payload.addon_codes:
            addons = session.query(Addon).filter(Addon.code.in_(payload.addon_codes)).all()
            addon_total = float(sum(float(addon.amount) for addon in addons))
        base_amount = float(plan_price.amount) if plan_price is not None else 0.0
        gross_amount = base_amount + addon_total
        final_amount = gross_amount * (1 - (payload.discount_percent / 100))
        session.add(
            SaasInvoice(
                tenant_id=tenant.id,
                amount=round(final_amount, 2),
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
                "addon_codes": payload.addon_codes,
                "issue_fiscal_document": payload.issue_fiscal_document,
            },
        )
    )
    session.commit()
    session.refresh(tenant)
    return tenant
