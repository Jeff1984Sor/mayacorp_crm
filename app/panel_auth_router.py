from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.deps import central_session_dep, tenant_context_dep, tenant_session_dep
from app.core.security import build_token, verify_password
from app.models.central import CentralUser, Tenant
from app.models.tenant import TenantSchemaVersion, TenantWhatsappAccount, User
from app.panel_common import (
    PanelCentralLoginRequest,
    PanelTenantCreateRequest,
    PanelTenantLoginRequest,
    panel_central_user_dep,
    panel_cookie_options,
    panel_response,
    panel_tenant_user_dep,
)
from app.schemas.tenant import TenantCreateRequest
from app.services.tenant_auth import issue_tenant_token_pair
from app.services.tenants import create_tenant

panel_auth_router = APIRouter(tags=["health"])


@panel_auth_router.get("/admin/panel", response_class=HTMLResponse)
def admin_panel() -> str:
    template_path = Path(__file__).resolve().parent / "templates" / "admin_panel.html"
    return template_path.read_text(encoding="utf-8")


@panel_auth_router.post("/admin/panel/login")
def admin_panel_login(
    payload: PanelCentralLoginRequest,
    response: Response,
    session: Session = Depends(central_session_dep),
) -> dict:
    user = session.query(CentralUser).filter(CentralUser.email == payload.email).one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    token = build_token(user.email, expires_in_minutes=60, extra={"scope": "central"}, token_type="access")
    response.set_cookie("panel_central_token", token, **panel_cookie_options())
    return panel_response(
        "Sessao central iniciada.",
        {"email": user.email, "full_name": user.full_name, "must_change_password": user.must_change_password},
    )


@panel_auth_router.post("/admin/panel/logout")
def admin_panel_logout(response: Response) -> dict:
    response.delete_cookie("panel_central_token", samesite="lax")
    response.delete_cookie("panel_tenant_token", samesite="lax")
    response.delete_cookie("panel_tenant_slug", samesite="lax")
    return panel_response("Sessao encerrada.", {"status": "logged_out"})


@panel_auth_router.get("/admin/panel/central/dashboard")
def admin_panel_central_dashboard(
    _: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    from app.models.central import CentralTask, SaasInvoice

    tenants = session.query(Tenant).all()
    invoices = session.query(SaasInvoice).all()
    open_tasks = session.query(CentralTask).filter(CentralTask.status == "open").count()
    return panel_response(
        "Dashboard central carregado.",
        {
            "tenant_count": len(tenants),
            "active_tenant_count": sum(1 for tenant in tenants if tenant.status == "active"),
            "open_task_count": open_tasks,
            "pending_invoice_count": sum(1 for invoice in invoices if invoice.status == "pending"),
            "total_invoice_amount": float(sum(float(invoice.amount) for invoice in invoices)),
        },
    )


@panel_auth_router.post("/admin/panel/tenant", status_code=201)
def admin_panel_create_tenant(
    payload: PanelTenantCreateRequest,
    current_user: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    tenant = create_tenant(
        session,
        TenantCreateRequest(
            company_name=payload.company_name,
            workspace_slug=payload.workspace_slug,
            company_document=None,
            admin_name=payload.admin_name,
            admin_email=payload.admin_email,
            admin_password=payload.admin_password,
            plan_code="starter",
            addon_codes=[],
            billing_day=5,
            discount_percent=0,
            generate_invoice=True,
            issue_fiscal_document=False,
        ),
        actor_email=current_user.email,
    )
    return panel_response("Tenant criado.", {"tenant_id": tenant.id, "workspace_slug": tenant.slug, "status": tenant.status})


@panel_auth_router.post("/admin/panel/{workspace_slug}/login")
def admin_panel_tenant_login(
    workspace_slug: str,
    payload: PanelTenantLoginRequest,
    response: Response,
    session: Session = Depends(tenant_session_dep),
) -> dict:
    user = session.query(User).filter(User.email == payload.email).one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    token, _ = issue_tenant_token_pair(
        user.email,
        is_admin=user.is_admin,
        must_change_password=user.must_change_password,
        role=user.role,
    )
    response.set_cookie("panel_tenant_token", token, **panel_cookie_options())
    response.set_cookie("panel_tenant_slug", workspace_slug, **panel_cookie_options())
    return panel_response("Sessao do tenant iniciada.", {"email": user.email, "role": user.role, "workspace_slug": workspace_slug})


@panel_auth_router.get("/admin/panel/{workspace_slug}/health")
def admin_panel_tenant_health(
    workspace_slug: str,
    tenant: Tenant = Depends(tenant_context_dep),
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_user_dep),
) -> dict:
    whatsapp = session.query(TenantWhatsappAccount).order_by(TenantWhatsappAccount.id.asc()).first()
    versions = session.query(TenantSchemaVersion).order_by(TenantSchemaVersion.id.asc()).all()
    return panel_response(
        "Health do tenant carregado.",
        {
            "workspace_slug": workspace_slug,
            "tenant_status": tenant.status,
            "plan_code": tenant.plan_code,
            "schema_versions": [item.version for item in versions],
            "whatsapp_status": whatsapp.status if whatsapp else None,
        },
    )
