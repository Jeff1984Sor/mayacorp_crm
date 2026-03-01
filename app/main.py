from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.api.deps import central_session_dep, tenant_context_dep, tenant_session_dep
from app.api.routes import _write_document_file, _write_signed_contract_file, router
from app.core.middleware import TenantResolutionMiddleware
from app.core.security import decode_token, verify_password
from app.models.central import CentralUser, Tenant
from app.models.tenant import (
    AccountsReceivable,
    Client,
    Contract,
    FinanceCategory,
    Lead,
    Proposal,
    SalesItem,
    SalesOrder,
    TenantWhatsappAccount,
    User,
)
from app.schemas.tenant import TenantCreateRequest
from app.services.bootstrap import bootstrap_central_database
from app.services.tenant_auth import issue_tenant_token_pair
from app.services.tenants import create_tenant


class PanelCentralLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4, max_length=128)


class PanelTenantLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4, max_length=128)


class PanelTenantCreateRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=255)
    workspace_slug: str = Field(min_length=2, max_length=80)
    admin_name: str = Field(min_length=2, max_length=255)
    admin_email: EmailStr
    admin_password: str = Field(min_length=4, max_length=128)


class PanelSalesOrderRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    quantity: float = Field(default=1, gt=0)
    unit_price: float = Field(gt=0)
    first_due_date: str


class PanelProposalRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    sales_order_id: int | None = None


class PanelContractRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    sales_order_id: int | None = None


class PanelContractSignRequest(BaseModel):
    contract_id: int
    file_name: str = Field(min_length=3, max_length=255)
    content: str = Field(min_length=1)


class PanelFinanceCategoryRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    entry_type: str = Field(default="both", max_length=20)


class PanelWhatsappSessionRequest(BaseModel):
    provider_session_id: str | None = Field(default=None, max_length=120)


class PanelLeadRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)


class PanelClientRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)


bootstrap_central_database()

app = FastAPI(
    title="Mayacorp CRM",
    version="0.1.0",
    description="API SaaS multi-tenant para CRM, ERP, WhatsApp, IA, financeiro e analytics.",
    openapi_tags=[
        {"name": "health", "description": "Healthcheck e operacao basica."},
        {"name": "central-auth", "description": "Autenticacao e gestao da conta central."},
        {"name": "central-saas", "description": "Administracao SaaS, tenants e dashboards centrais."},
        {"name": "tenant-auth", "description": "Autenticacao do workspace."},
        {"name": "tenant-users", "description": "Usuarios, papeis e permissoes do tenant."},
        {"name": "crm", "description": "Leads, clients e operacoes comerciais."},
        {"name": "finance", "description": "Financeiro, categorias, centros de custo e dashboards."},
        {"name": "documents", "description": "Propostas, contratos e assinatura."},
        {"name": "whatsapp", "description": "Sessao, mensagens e inbox."},
        {"name": "ai", "description": "Configuracao e uso de IA."},
        {"name": "analytics", "description": "Analytics central e snapshots."},
        {"name": "marketplace", "description": "Integracoes de marketplace."},
        {"name": "storage", "description": "Storage por workspace e acesso assinado."},
        {"name": "leadradar", "description": "Captura e processamento de lead radar."},
    ],
)
app.add_middleware(TenantResolutionMiddleware)
app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent / "static"), name="static")
app.include_router(router)


def panel_central_user_dep(
    panel_central_token: str | None = Cookie(default=None),
    session: Session = Depends(central_session_dep),
) -> CentralUser:
    if not panel_central_token:
        raise HTTPException(status_code=401, detail="Panel central session required.")
    try:
        payload = decode_token(panel_central_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid panel central session.")
    if payload.get("scope") != "central":
        raise HTTPException(status_code=403, detail="Invalid panel central scope.")
    user = session.query(CentralUser).filter(CentralUser.email == payload.get("sub")).one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found.")
    return user


def panel_tenant_user_dep(
    panel_tenant_token: str | None = Cookie(default=None),
    session: Session = Depends(tenant_session_dep),
) -> User:
    if not panel_tenant_token:
        raise HTTPException(status_code=401, detail="Panel tenant session required.")
    try:
        payload = decode_token(panel_tenant_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid panel tenant session.")
    if payload.get("scope") != "tenant" or payload.get("type") != "access":
        raise HTTPException(status_code=403, detail="Invalid panel tenant scope.")
    user = session.query(User).filter(User.email == payload.get("sub")).one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found.")
    return user


def panel_tenant_permission_dep(permission: str):
    def dependency(current_user: User = Depends(panel_tenant_user_dep)) -> User:
        if current_user.is_admin or current_user.role == "admin":
            return current_user
        granted = current_user.permissions or {}
        if not granted.get(permission, False):
            raise HTTPException(status_code=403, detail=f"Permission required: {permission}")
        return current_user

    return dependency


@app.get("/admin/panel", response_class=HTMLResponse, tags=["health"])
def admin_panel() -> str:
    template_path = Path(__file__).resolve().parent / "templates" / "admin_panel.html"
    return template_path.read_text(encoding="utf-8")


@app.post("/admin/panel/login", tags=["health"])
def admin_panel_login(
    payload: PanelCentralLoginRequest,
    response: Response,
    session: Session = Depends(central_session_dep),
) -> dict:
    user = session.query(CentralUser).filter(CentralUser.email == payload.email).one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    from app.core.security import build_token

    token = build_token(user.email, expires_in_minutes=60, extra={"scope": "central"}, token_type="access")
    response.set_cookie("panel_central_token", token, httponly=True, samesite="lax")
    return {"email": user.email, "full_name": user.full_name, "must_change_password": user.must_change_password}


@app.post("/admin/panel/logout", tags=["health"])
def admin_panel_logout(response: Response) -> dict:
    response.delete_cookie("panel_central_token")
    response.delete_cookie("panel_tenant_token")
    response.delete_cookie("panel_tenant_slug")
    return {"status": "logged_out"}


@app.get("/admin/panel/central/dashboard", tags=["health"])
def admin_panel_central_dashboard(
    _: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    from app.models.central import CentralTask, SaasInvoice

    tenants = session.query(Tenant).all()
    invoices = session.query(SaasInvoice).all()
    open_tasks = session.query(CentralTask).filter(CentralTask.status == "open").count()
    return {
        "tenant_count": len(tenants),
        "active_tenant_count": sum(1 for tenant in tenants if tenant.status == "active"),
        "open_task_count": open_tasks,
        "pending_invoice_count": sum(1 for invoice in invoices if invoice.status == "pending"),
        "total_invoice_amount": float(sum(float(invoice.amount) for invoice in invoices)),
    }


@app.post("/admin/panel/tenant", status_code=201, tags=["health"])
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
    return {"tenant_id": tenant.id, "workspace_slug": tenant.slug, "status": tenant.status}


@app.post("/admin/panel/{workspace_slug}/login", tags=["health"])
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
    response.set_cookie("panel_tenant_token", token, httponly=True, samesite="lax")
    response.set_cookie("panel_tenant_slug", workspace_slug, httponly=True, samesite="lax")
    return {"email": user.email, "role": user.role, "workspace_slug": workspace_slug}


@app.get("/admin/panel/{workspace_slug}/health", tags=["health"])
def admin_panel_tenant_health(
    workspace_slug: str,
    tenant: Tenant = Depends(tenant_context_dep),
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_user_dep),
) -> dict:
    from app.models.tenant import TenantSchemaVersion

    whatsapp = session.query(TenantWhatsappAccount).order_by(TenantWhatsappAccount.id.asc()).first()
    versions = session.query(TenantSchemaVersion).order_by(TenantSchemaVersion.id.asc()).all()
    return {
        "workspace_slug": workspace_slug,
        "tenant_status": tenant.status,
        "plan_code": tenant.plan_code,
        "schema_versions": [item.version for item in versions],
        "whatsapp_status": whatsapp.status if whatsapp else None,
    }


@app.post("/admin/panel/{workspace_slug}/lead", status_code=201, tags=["health"])
def admin_panel_create_lead(
    payload: PanelLeadRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    lead = Lead(name=payload.name, email=payload.email, phone=payload.phone, source="panel")
    session.add(lead)
    session.commit()
    session.refresh(lead)
    return {"id": lead.id, "name": lead.name, "email": lead.email, "phone": lead.phone}


@app.post("/admin/panel/{workspace_slug}/client", status_code=201, tags=["health"])
def admin_panel_create_client(
    payload: PanelClientRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    client = Client(name=payload.name, email=payload.email, phone=payload.phone)
    session.add(client)
    session.commit()
    session.refresh(client)
    return {"id": client.id, "name": client.name, "email": client.email, "phone": client.phone}


@app.post("/admin/panel/{workspace_slug}/sales-order", tags=["health"])
def admin_panel_create_sales_order(
    workspace_slug: str,
    payload: PanelSalesOrderRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    total_amount = (Decimal(str(payload.quantity)) * Decimal(str(payload.unit_price))).quantize(Decimal("0.01"))
    order = SalesOrder(client_id=None, order_type="one_time", duration_months=None, total_amount=total_amount, status="confirmed")
    session.add(order)
    session.flush()
    session.add(SalesItem(sales_order_id=order.id, description=payload.title, quantity=payload.quantity, unit_price=payload.unit_price))
    session.add(
        AccountsReceivable(
            sales_order_id=order.id,
            due_date=date.fromisoformat(payload.first_due_date),
            amount=total_amount,
            status="pending",
            category="Vendas",
            cost_center="Comercial",
        )
    )
    session.commit()
    return {"id": order.id, "status": order.status, "total_amount": float(total_amount), "workspace_slug": workspace_slug}


@app.post("/admin/panel/{workspace_slug}/proposal", tags=["health"])
def admin_panel_create_proposal(
    workspace_slug: str,
    payload: PanelProposalRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    if payload.sales_order_id is not None:
        order = session.query(SalesOrder).filter(SalesOrder.id == payload.sales_order_id).one_or_none()
        if order is None:
            raise HTTPException(status_code=404, detail="Sales order not found.")
    proposal = Proposal(title=payload.title, client_id=None, sales_order_id=payload.sales_order_id, template_name="panel-default", is_sendable=True)
    session.add(proposal)
    session.commit()
    session.refresh(proposal)
    proposal.pdf_path = _write_document_file(workspace_slug, "proposals", proposal.id, proposal.title)
    session.commit()
    return {"id": proposal.id, "title": proposal.title, "pdf_path": proposal.pdf_path}


@app.post("/admin/panel/{workspace_slug}/contract", tags=["health"])
def admin_panel_create_contract(
    workspace_slug: str,
    payload: PanelContractRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("contracts.write")),
) -> dict:
    if payload.sales_order_id is not None:
        order = session.query(SalesOrder).filter(SalesOrder.id == payload.sales_order_id).one_or_none()
        if order is None:
            raise HTTPException(status_code=404, detail="Sales order not found.")
    contract = Contract(title=payload.title, client_id=None, sales_order_id=payload.sales_order_id, template_name="panel-default")
    session.add(contract)
    session.commit()
    session.refresh(contract)
    contract.pdf_path = _write_document_file(workspace_slug, "contracts", contract.id, contract.title)
    session.commit()
    return {"id": contract.id, "title": contract.title, "status": contract.status, "pdf_path": contract.pdf_path}


@app.post("/admin/panel/{workspace_slug}/contract/sign", tags=["health"])
def admin_panel_sign_contract(
    workspace_slug: str,
    payload: PanelContractSignRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("contracts.write")),
) -> dict:
    contract = session.query(Contract).filter(Contract.id == payload.contract_id).one_or_none()
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found.")
    contract.signed_file_path = _write_signed_contract_file(workspace_slug, contract.id, payload.file_name, payload.content)
    contract.status = "signed"
    session.commit()
    return {"id": contract.id, "status": contract.status, "signed_file_path": contract.signed_file_path}


@app.get("/admin/panel/{workspace_slug}/summary", tags=["health"])
def admin_panel_workspace_summary(
    workspace_slug: str,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    sales_orders = session.query(SalesOrder).order_by(SalesOrder.id.desc()).limit(5).all()
    proposals = session.query(Proposal).order_by(Proposal.id.desc()).limit(5).all()
    contracts = session.query(Contract).order_by(Contract.id.desc()).limit(5).all()
    categories = session.query(FinanceCategory).order_by(FinanceCategory.name.asc()).limit(10).all()
    leads = session.query(Lead).order_by(Lead.id.desc()).limit(5).all()
    clients = session.query(Client).order_by(Client.id.desc()).limit(5).all()
    whatsapp = session.query(TenantWhatsappAccount).order_by(TenantWhatsappAccount.id.asc()).first()

    receivables = session.query(AccountsReceivable).all()
    receivable_total = float(sum(float(item.amount) for item in receivables))
    receivable_pending = float(sum(float(item.amount) for item in receivables if item.status == "pending"))

    return {
        "workspace_slug": workspace_slug,
        "sales_orders": [{"id": item.id, "status": item.status, "total_amount": float(item.total_amount)} for item in sales_orders],
        "proposals": [{"id": item.id, "title": item.title, "pdf_path": item.pdf_path} for item in proposals],
        "contracts": [{"id": item.id, "title": item.title, "status": item.status, "signed_file_path": item.signed_file_path} for item in contracts],
        "leads": [{"id": item.id, "name": item.name, "email": item.email, "phone": item.phone} for item in leads],
        "clients": [{"id": item.id, "name": item.name, "email": item.email, "phone": item.phone} for item in clients],
        "finance": {
            "category_count": len(categories),
            "categories": [{"id": item.id, "name": item.name, "entry_type": item.entry_type} for item in categories],
            "receivable_total": receivable_total,
            "receivable_pending": receivable_pending,
        },
        "whatsapp": (
            {
                "id": whatsapp.id,
                "provider_session_id": whatsapp.provider_session_id,
                "status": whatsapp.status,
                "last_qr_code": whatsapp.last_qr_code,
            }
            if whatsapp is not None
            else None
        ),
        "generated_at": datetime.now(UTC).isoformat(),
    }


@app.post("/admin/panel/{workspace_slug}/finance-category", status_code=201, tags=["health"])
def admin_panel_create_finance_category(
    workspace_slug: str,
    payload: PanelFinanceCategoryRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("finance.write")),
) -> dict:
    category = FinanceCategory(name=payload.name, entry_type=payload.entry_type)
    session.add(category)
    session.commit()
    session.refresh(category)
    return {"id": category.id, "name": category.name, "entry_type": category.entry_type, "workspace_slug": workspace_slug}


@app.post("/admin/panel/{workspace_slug}/whatsapp-session", tags=["health"])
def admin_panel_upsert_whatsapp_session(
    workspace_slug: str,
    payload: PanelWhatsappSessionRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("whatsapp.manage")),
) -> dict:
    account = session.query(TenantWhatsappAccount).order_by(TenantWhatsappAccount.id.asc()).first()
    if account is None:
        account = TenantWhatsappAccount(provider_session_id=payload.provider_session_id, status="connecting", last_qr_code="qr-placeholder")
        session.add(account)
    else:
        account.provider_session_id = payload.provider_session_id
        account.status = "connecting"
        account.last_qr_code = "qr-placeholder"
    session.commit()
    session.refresh(account)
    return {
        "id": account.id,
        "workspace_slug": workspace_slug,
        "provider_session_id": account.provider_session_id,
        "status": account.status,
        "last_qr_code": account.last_qr_code,
    }
