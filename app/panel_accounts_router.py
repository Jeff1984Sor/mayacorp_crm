from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import central_session_dep
from app.models.central import CompanyAccount, CentralAuditLog, CentralUser, Plan, Tenant, TenantSubscription
from app.panel_common import (
    PanelCompanyAccountPlanRequest,
    PanelCompanyAccountRequest,
    panel_central_user_dep,
    panel_response,
)

panel_accounts_router = APIRouter(tags=["health"])

ALLOWED_ACCOUNT_STAGES = {"lead", "client"}


def _ensure_account_stage(stage: str) -> str:
    if stage not in ALLOWED_ACCOUNT_STAGES:
        raise HTTPException(status_code=422, detail=f"Invalid account stage: {stage}")
    return stage


def _serialize_plan_price(plan: Plan) -> dict | None:
    if not plan.prices:
        return None
    price = sorted(plan.prices, key=lambda item: item.id)[0]
    return {
        "billing_cycle": price.billing_cycle,
        "amount": float(price.amount),
        "currency": price.currency,
    }


def _serialize_account_plan(account: CompanyAccount, tenant: Tenant | None, subscription: TenantSubscription | None, plans: list[Plan]) -> dict:
    return {
        "account_id": account.id,
        "account_name": account.name,
        "tenant_id": tenant.id if tenant else None,
        "tenant_slug": tenant.slug if tenant else None,
        "has_tenant": tenant is not None,
        "tenant_status": tenant.status if tenant else None,
        "plan_code": tenant.plan_code if tenant else None,
        "billing_day": tenant.billing_day if tenant else None,
        "discount_percent": float(tenant.discount_percent) if tenant else None,
        "subscription": (
            {
                "id": subscription.id,
                "plan_code": subscription.plan_code,
                "status": subscription.status,
                "started_on": subscription.started_on.isoformat(),
                "discount_percent": float(subscription.discount_percent),
            }
            if subscription
            else None
        ),
        "available_plans": [
            {
                "code": plan.code,
                "name": plan.name,
                "price": _serialize_plan_price(plan),
            }
            for plan in plans
        ],
    }


@panel_accounts_router.get("/admin/panel/accounts")
def admin_panel_list_accounts(
    _: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    accounts = session.query(CompanyAccount).order_by(CompanyAccount.updated_at.desc(), CompanyAccount.id.desc()).all()
    tenant_ids = [account.tenant_id for account in accounts if account.tenant_id]
    tenant_lookup = {}
    if tenant_ids:
        tenant_lookup = {
            tenant.id: tenant
            for tenant in session.query(Tenant).filter(Tenant.id.in_(tenant_ids)).all()
        }
    return panel_response(
        "Contas carregadas.",
        {
            "items": [
                {
                    "id": account.id,
                    "name": account.name,
                    "lifecycle_stage": account.lifecycle_stage,
                    "admin_email": account.admin_email,
                    "phone": account.phone,
                    "company_document": account.company_document,
                    "tenant_id": account.tenant_id,
                    "tenant_slug": tenant_lookup.get(account.tenant_id).slug if account.tenant_id in tenant_lookup else None,
                    "notes": account.notes,
                    "last_converted_at": account.last_converted_at.isoformat() if account.last_converted_at else None,
                    "updated_at": account.updated_at.isoformat(),
                }
                for account in accounts
            ],
            "total": len(accounts),
        },
    )


@panel_accounts_router.post("/admin/panel/account", status_code=201)
def admin_panel_create_account(
    payload: PanelCompanyAccountRequest,
    current_user: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    stage = _ensure_account_stage(payload.lifecycle_stage)
    account = CompanyAccount(
        name=payload.name,
        lifecycle_stage=stage,
        admin_email=payload.admin_email,
        phone=payload.phone,
        company_document=payload.company_document,
        notes=payload.notes,
        last_converted_at=datetime.now(UTC) if stage == "client" else None,
    )
    session.add(account)
    session.flush()
    session.add(
        CentralAuditLog(
            actor_email=current_user.email,
            action="account.created",
            target_type="company_account",
            target_id=str(account.id),
            payload={"stage": stage, "tenant_id": account.tenant_id},
        )
    )
    session.commit()
    return panel_response(
        "Conta criada.",
        {
            "id": account.id,
            "name": account.name,
            "lifecycle_stage": account.lifecycle_stage,
            "admin_email": account.admin_email,
            "tenant_id": account.tenant_id,
        },
    )


@panel_accounts_router.patch("/admin/panel/account/{account_id}")
def admin_panel_update_account(
    account_id: int,
    payload: PanelCompanyAccountRequest,
    current_user: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    account = session.query(CompanyAccount).filter(CompanyAccount.id == account_id).one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="Company account not found.")
    next_stage = _ensure_account_stage(payload.lifecycle_stage)
    if account.lifecycle_stage != "client" and next_stage == "client":
        account.last_converted_at = datetime.now(UTC)
    account.name = payload.name
    account.lifecycle_stage = next_stage
    account.admin_email = payload.admin_email
    account.phone = payload.phone
    account.company_document = payload.company_document
    account.notes = payload.notes
    session.add(
        CentralAuditLog(
            actor_email=current_user.email,
            action="account.updated",
            target_type="company_account",
            target_id=str(account.id),
            payload={"stage": next_stage, "tenant_id": account.tenant_id},
        )
    )
    session.commit()
    return panel_response(
        "Conta atualizada.",
        {
            "id": account.id,
            "name": account.name,
            "lifecycle_stage": account.lifecycle_stage,
            "admin_email": account.admin_email,
            "tenant_id": account.tenant_id,
            "last_converted_at": account.last_converted_at.isoformat() if account.last_converted_at else None,
        },
    )


@panel_accounts_router.post("/admin/panel/account/{account_id}/convert")
def admin_panel_convert_account(
    account_id: int,
    current_user: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    account = session.query(CompanyAccount).filter(CompanyAccount.id == account_id).one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="Company account not found.")
    previous_stage = account.lifecycle_stage
    if account.lifecycle_stage != "client":
        account.lifecycle_stage = "client"
        account.last_converted_at = datetime.now(UTC)
    session.add(
        CentralAuditLog(
            actor_email=current_user.email,
            action="account.converted",
            target_type="company_account",
            target_id=str(account.id),
            payload={"from_stage": previous_stage, "to_stage": account.lifecycle_stage, "tenant_id": account.tenant_id},
        )
    )
    session.commit()
    return panel_response(
        "Conta convertida para client.",
        {
            "id": account.id,
            "name": account.name,
            "lifecycle_stage": account.lifecycle_stage,
            "admin_email": account.admin_email,
            "tenant_id": account.tenant_id,
            "last_converted_at": account.last_converted_at.isoformat() if account.last_converted_at else None,
        },
    )


@panel_accounts_router.get("/admin/panel/account/{account_id}/plan")
def admin_panel_get_account_plan(
    account_id: int,
    _: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    account = session.query(CompanyAccount).filter(CompanyAccount.id == account_id).one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="Company account not found.")
    tenant = None
    subscription = None
    if account.tenant_id:
        tenant = session.query(Tenant).filter(Tenant.id == account.tenant_id).one_or_none()
        if tenant:
            subscription = (
                session.query(TenantSubscription)
                .filter(TenantSubscription.tenant_id == tenant.id)
                .order_by(TenantSubscription.started_on.desc(), TenantSubscription.id.desc())
                .first()
            )
    plans = (
        session.query(Plan)
        .filter(Plan.is_active.is_(True))
        .order_by(Plan.name.asc(), Plan.id.asc())
        .all()
    )
    return panel_response("Plano do cliente carregado.", _serialize_account_plan(account, tenant, subscription, plans))


@panel_accounts_router.patch("/admin/panel/account/{account_id}/plan")
def admin_panel_update_account_plan(
    account_id: int,
    payload: PanelCompanyAccountPlanRequest,
    current_user: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    account = session.query(CompanyAccount).filter(CompanyAccount.id == account_id).one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="Company account not found.")
    if not account.tenant_id:
        raise HTTPException(status_code=409, detail="Company account does not have a tenant yet.")
    tenant = session.query(Tenant).filter(Tenant.id == account.tenant_id).one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found.")
    plan = session.query(Plan).filter(Plan.code == payload.plan_code, Plan.is_active.is_(True)).one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found.")
    tenant.plan_code = plan.code
    tenant.status = payload.status
    tenant.billing_day = payload.billing_day
    tenant.discount_percent = payload.discount_percent
    subscription = (
        session.query(TenantSubscription)
        .filter(TenantSubscription.tenant_id == tenant.id)
        .order_by(TenantSubscription.started_on.desc(), TenantSubscription.id.desc())
        .first()
    )
    if subscription is None:
        subscription = TenantSubscription(
            tenant_id=tenant.id,
            started_on=date.today(),
        )
        session.add(subscription)
    subscription.plan_code = plan.code
    subscription.status = payload.status
    subscription.discount_percent = payload.discount_percent
    session.add(
        CentralAuditLog(
            actor_email=current_user.email,
            action="account.plan_updated",
            target_type="company_account",
            target_id=str(account.id),
            payload={
                "tenant_id": tenant.id,
                "plan_code": plan.code,
                "status": payload.status,
                "billing_day": payload.billing_day,
                "discount_percent": payload.discount_percent,
            },
        )
    )
    session.commit()
    plans = (
        session.query(Plan)
        .filter(Plan.is_active.is_(True))
        .order_by(Plan.name.asc(), Plan.id.asc())
        .all()
    )
    return panel_response("Plano do cliente atualizado.", _serialize_account_plan(account, tenant, subscription, plans))
