from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import central_session_dep, tenant_context_dep, tenant_session_dep
from app.api.routes import _write_document_file, _write_signed_contract_file, router
from app.core.middleware import TenantResolutionMiddleware
from app.core.security import verify_password
from app.models.central import CentralUser, Tenant
from app.models.tenant import (
    AccountsPayable,
    AccountsReceivable,
    Client,
    Contract,
    FinanceCategory,
    Lead,
    Message,
    Proposal,
    SalesItem,
    SalesOrder,
    TenantWhatsappAccount,
    User,
)
from app.panel_common import (
    PanelCentralLoginRequest,
    PanelClientRequest,
    PanelContractRequest,
    PanelContractSignRequest,
    PanelFinanceCategoryRequest,
    PanelFinanceEntryRequest,
    PanelLeadRequest,
    PanelProposalRequest,
    PanelSalesOrderRequest,
    PanelStatusRequest,
    PanelTenantCreateRequest,
    PanelTenantLoginRequest,
    PanelWhatsappSendRequest,
    PanelWhatsappSessionRequest,
    panel_central_user_dep,
    panel_cookie_options,
    panel_response,
    panel_tenant_permission_dep,
    panel_tenant_user_dep,
)
from app.schemas.tenant import TenantCreateRequest
from app.services.bootstrap import bootstrap_central_database
from app.services.tenant_auth import issue_tenant_token_pair
from app.services.tenants import create_tenant


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
    response.set_cookie("panel_central_token", token, **panel_cookie_options())
    return panel_response(
        "Sessao central iniciada.",
        {"email": user.email, "full_name": user.full_name, "must_change_password": user.must_change_password},
    )


@app.post("/admin/panel/logout", tags=["health"])
def admin_panel_logout(response: Response) -> dict:
    response.delete_cookie("panel_central_token", samesite="lax")
    response.delete_cookie("panel_tenant_token", samesite="lax")
    response.delete_cookie("panel_tenant_slug", samesite="lax")
    return panel_response("Sessao encerrada.", {"status": "logged_out"})


@app.get("/admin/panel/central/dashboard", tags=["health"])
def admin_panel_central_dashboard(
    _: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    from app.models.central import CentralTask, SaasInvoice

    tenants = session.query(Tenant).all()
    invoices = session.query(SaasInvoice).all()
    open_tasks = session.query(CentralTask).filter(CentralTask.status == "open").count()
    return panel_response("Dashboard central carregado.", {
        "tenant_count": len(tenants),
        "active_tenant_count": sum(1 for tenant in tenants if tenant.status == "active"),
        "open_task_count": open_tasks,
        "pending_invoice_count": sum(1 for invoice in invoices if invoice.status == "pending"),
        "total_invoice_amount": float(sum(float(invoice.amount) for invoice in invoices)),
    })


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
    return panel_response(
        "Tenant criado.",
        {"tenant_id": tenant.id, "workspace_slug": tenant.slug, "status": tenant.status},
    )


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
    response.set_cookie("panel_tenant_token", token, **panel_cookie_options())
    response.set_cookie("panel_tenant_slug", workspace_slug, **panel_cookie_options())
    return panel_response(
        "Sessao do tenant iniciada.",
        {"email": user.email, "role": user.role, "workspace_slug": workspace_slug},
    )


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
    return panel_response("Health do tenant carregado.", {
        "workspace_slug": workspace_slug,
        "tenant_status": tenant.status,
        "plan_code": tenant.plan_code,
        "schema_versions": [item.version for item in versions],
        "whatsapp_status": whatsapp.status if whatsapp else None,
    })


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
    return panel_response("Lead criado.", {"id": lead.id, "name": lead.name, "email": lead.email, "phone": lead.phone})


@app.patch("/admin/panel/{workspace_slug}/lead/{lead_id}", tags=["health"])
def admin_panel_update_lead(
    lead_id: int,
    payload: PanelLeadRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    lead = session.query(Lead).filter(Lead.id == lead_id).one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    lead.name = payload.name
    lead.email = payload.email
    lead.phone = payload.phone
    session.commit()
    return panel_response("Lead atualizado.", {"id": lead.id, "name": lead.name, "email": lead.email, "phone": lead.phone})


@app.delete("/admin/panel/{workspace_slug}/lead/{lead_id}", tags=["health"])
def admin_panel_delete_lead(
    lead_id: int,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    lead = session.query(Lead).filter(Lead.id == lead_id).one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    session.delete(lead)
    session.commit()
    return panel_response("Lead removido.", {"status": "deleted", "id": lead_id})


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
    return panel_response("Client criado.", {"id": client.id, "name": client.name, "email": client.email, "phone": client.phone})


@app.patch("/admin/panel/{workspace_slug}/client/{client_id}", tags=["health"])
def admin_panel_update_client(
    client_id: int,
    payload: PanelClientRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    client = session.query(Client).filter(Client.id == client_id).one_or_none()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found.")
    client.name = payload.name
    client.email = payload.email
    client.phone = payload.phone
    session.commit()
    return panel_response("Client atualizado.", {"id": client.id, "name": client.name, "email": client.email, "phone": client.phone})


@app.delete("/admin/panel/{workspace_slug}/client/{client_id}", tags=["health"])
def admin_panel_delete_client(
    client_id: int,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    client = session.query(Client).filter(Client.id == client_id).one_or_none()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found.")
    session.delete(client)
    session.commit()
    return panel_response("Client removido.", {"status": "deleted", "id": client_id})


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
    return panel_response(
        "Pedido criado.",
        {"id": order.id, "status": order.status, "total_amount": float(total_amount), "workspace_slug": workspace_slug},
    )


@app.patch("/admin/panel/{workspace_slug}/sales-order/{order_id}", tags=["health"])
def admin_panel_update_sales_order(
    order_id: int,
    payload: PanelStatusRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    order = session.query(SalesOrder).filter(SalesOrder.id == order_id).one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Sales order not found.")
    order.status = payload.status
    session.commit()
    return panel_response("Pedido atualizado.", {"id": order.id, "status": order.status})


@app.delete("/admin/panel/{workspace_slug}/sales-order/{order_id}", tags=["health"])
def admin_panel_delete_sales_order(
    order_id: int,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    order = session.query(SalesOrder).filter(SalesOrder.id == order_id).one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Sales order not found.")
    session.query(AccountsReceivable).filter(AccountsReceivable.sales_order_id == order.id).delete()
    session.query(SalesItem).filter(SalesItem.sales_order_id == order.id).delete()
    session.delete(order)
    session.commit()
    return panel_response("Pedido removido.", {"status": "deleted", "id": order_id})


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
    return panel_response("Proposta criada.", {"id": proposal.id, "title": proposal.title, "pdf_path": proposal.pdf_path})


@app.patch("/admin/panel/{workspace_slug}/proposal/{proposal_id}", tags=["health"])
def admin_panel_update_proposal(
    workspace_slug: str,
    proposal_id: int,
    payload: PanelProposalRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    proposal = session.query(Proposal).filter(Proposal.id == proposal_id).one_or_none()
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found.")
    proposal.title = payload.title
    proposal.sales_order_id = payload.sales_order_id
    proposal.pdf_path = _write_document_file(workspace_slug, "proposals", proposal.id, proposal.title)
    session.commit()
    return panel_response("Proposta atualizada.", {"id": proposal.id, "title": proposal.title, "pdf_path": proposal.pdf_path})


@app.delete("/admin/panel/{workspace_slug}/proposal/{proposal_id}", tags=["health"])
def admin_panel_delete_proposal(
    proposal_id: int,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    proposal = session.query(Proposal).filter(Proposal.id == proposal_id).one_or_none()
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found.")
    session.delete(proposal)
    session.commit()
    return panel_response("Proposta removida.", {"status": "deleted", "id": proposal_id})


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
    return panel_response(
        "Contrato criado.",
        {"id": contract.id, "title": contract.title, "status": contract.status, "pdf_path": contract.pdf_path},
    )


@app.patch("/admin/panel/{workspace_slug}/contract/{contract_id}", tags=["health"])
def admin_panel_update_contract(
    workspace_slug: str,
    contract_id: int,
    payload: PanelContractRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("contracts.write")),
) -> dict:
    contract = session.query(Contract).filter(Contract.id == contract_id).one_or_none()
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found.")
    contract.title = payload.title
    contract.sales_order_id = payload.sales_order_id
    contract.pdf_path = _write_document_file(workspace_slug, "contracts", contract.id, contract.title)
    session.commit()
    return panel_response(
        "Contrato atualizado.",
        {"id": contract.id, "title": contract.title, "status": contract.status, "pdf_path": contract.pdf_path},
    )


@app.delete("/admin/panel/{workspace_slug}/contract/{contract_id}", tags=["health"])
def admin_panel_delete_contract(
    contract_id: int,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("contracts.write")),
) -> dict:
    contract = session.query(Contract).filter(Contract.id == contract_id).one_or_none()
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found.")
    session.delete(contract)
    session.commit()
    return panel_response("Contrato removido.", {"status": "deleted", "id": contract_id})


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
    return panel_response(
        "Contrato assinado.",
        {"id": contract.id, "status": contract.status, "signed_file_path": contract.signed_file_path},
    )


@app.get("/admin/panel/{workspace_slug}/summary", tags=["health"])
def admin_panel_workspace_summary(
    workspace_slug: str,
    page: int = 1,
    page_size: int = 5,
    q: str | None = None,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    page = max(page, 1)
    page_size = max(1, min(page_size, 20))
    offset = (page - 1) * page_size

    sales_orders = session.query(SalesOrder).order_by(SalesOrder.id.desc()).offset(offset).limit(page_size).all()
    proposals_query = session.query(Proposal).order_by(Proposal.id.desc())
    contracts_query = session.query(Contract).order_by(Contract.id.desc())
    leads_query = session.query(Lead).order_by(Lead.id.desc())
    clients_query = session.query(Client).order_by(Client.id.desc())
    if q:
        like_q = f"%{q}%"
        lowered_q = like_q.lower()
        proposals_query = proposals_query.filter(func.lower(Proposal.title).like(lowered_q))
        contracts_query = contracts_query.filter(func.lower(Contract.title).like(lowered_q))
        leads_query = leads_query.filter(func.lower(Lead.name).like(lowered_q))
        clients_query = clients_query.filter(func.lower(Client.name).like(lowered_q))
    proposals = proposals_query.offset(offset).limit(page_size).all()
    contracts = contracts_query.offset(offset).limit(page_size).all()
    categories = session.query(FinanceCategory).order_by(FinanceCategory.name.asc()).limit(10).all()
    leads = leads_query.offset(offset).limit(page_size).all()
    clients = clients_query.offset(offset).limit(page_size).all()
    whatsapp = session.query(TenantWhatsappAccount).order_by(TenantWhatsappAccount.id.asc()).first()

    receivables = session.query(AccountsReceivable).order_by(AccountsReceivable.id.desc()).limit(5).all()
    payables = session.query(AccountsPayable).order_by(AccountsPayable.id.desc()).limit(5).all()
    messages = session.query(Message).order_by(Message.id.desc()).limit(5).all()
    all_receivables = session.query(AccountsReceivable).all()
    receivable_total = float(sum(float(item.amount) for item in all_receivables))
    receivable_pending = float(sum(float(item.amount) for item in all_receivables if item.status == "pending"))

    return panel_response("Resumo carregado.", {
        "workspace_slug": workspace_slug,
        "sales_orders": [{"id": item.id, "status": item.status, "total_amount": float(item.total_amount)} for item in sales_orders],
        "proposals": [{"id": item.id, "title": item.title, "pdf_path": item.pdf_path} for item in proposals],
        "contracts": [{"id": item.id, "title": item.title, "status": item.status, "signed_file_path": item.signed_file_path} for item in contracts],
        "leads": [{"id": item.id, "name": item.name, "email": item.email, "phone": item.phone} for item in leads],
        "clients": [{"id": item.id, "name": item.name, "email": item.email, "phone": item.phone} for item in clients],
        "receivables": [{"id": item.id, "amount": float(item.amount), "status": item.status} for item in receivables],
        "payables": [{"id": item.id, "amount": float(item.amount), "status": item.status} for item in payables],
        "messages": [{"id": item.id, "direction": item.direction, "status": item.status, "body": item.body} for item in messages],
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
        "page": page,
        "page_size": page_size,
        "query": q,
    })


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
    return panel_response(
        "Categoria criada.",
        {"id": category.id, "name": category.name, "entry_type": category.entry_type, "workspace_slug": workspace_slug},
    )


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
    return panel_response("Sessao WhatsApp atualizada.", {
        "id": account.id,
        "workspace_slug": workspace_slug,
        "provider_session_id": account.provider_session_id,
        "status": account.status,
        "last_qr_code": account.last_qr_code,
    })


@app.post("/admin/panel/{workspace_slug}/finance/receivable", status_code=201, tags=["health"])
def admin_panel_create_receivable(
    payload: PanelFinanceEntryRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("finance.write")),
) -> dict:
    entry = AccountsReceivable(
        due_date=date.fromisoformat(payload.due_date),
        amount=payload.amount,
        status=payload.status,
        category=payload.category,
        cost_center=payload.cost_center,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return panel_response("Conta a receber criada.", {"id": entry.id, "status": entry.status, "amount": float(entry.amount)})


@app.patch("/admin/panel/{workspace_slug}/finance/receivable/{entry_id}", tags=["health"])
def admin_panel_update_receivable(
    entry_id: int,
    payload: PanelStatusRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("finance.write")),
) -> dict:
    entry = session.query(AccountsReceivable).filter(AccountsReceivable.id == entry_id).one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Accounts receivable not found.")
    entry.status = payload.status
    session.commit()
    return panel_response("Conta a receber atualizada.", {"id": entry.id, "status": entry.status})


@app.delete("/admin/panel/{workspace_slug}/finance/receivable/{entry_id}", tags=["health"])
def admin_panel_delete_receivable(
    entry_id: int,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("finance.write")),
) -> dict:
    entry = session.query(AccountsReceivable).filter(AccountsReceivable.id == entry_id).one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Accounts receivable not found.")
    session.delete(entry)
    session.commit()
    return panel_response("Conta a receber removida.", {"id": entry_id, "status": "deleted"})


@app.post("/admin/panel/{workspace_slug}/finance/payable", status_code=201, tags=["health"])
def admin_panel_create_payable(
    payload: PanelFinanceEntryRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("finance.write")),
) -> dict:
    entry = AccountsPayable(
        due_date=date.fromisoformat(payload.due_date),
        amount=payload.amount,
        status=payload.status,
        category=payload.category,
        cost_center=payload.cost_center,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return panel_response("Conta a pagar criada.", {"id": entry.id, "status": entry.status, "amount": float(entry.amount)})


@app.patch("/admin/panel/{workspace_slug}/finance/payable/{entry_id}", tags=["health"])
def admin_panel_update_payable(
    entry_id: int,
    payload: PanelStatusRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("finance.write")),
) -> dict:
    entry = session.query(AccountsPayable).filter(AccountsPayable.id == entry_id).one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Accounts payable not found.")
    entry.status = payload.status
    session.commit()
    return panel_response("Conta a pagar atualizada.", {"id": entry.id, "status": entry.status})


@app.delete("/admin/panel/{workspace_slug}/finance/payable/{entry_id}", tags=["health"])
def admin_panel_delete_payable(
    entry_id: int,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("finance.write")),
) -> dict:
    entry = session.query(AccountsPayable).filter(AccountsPayable.id == entry_id).one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Accounts payable not found.")
    session.delete(entry)
    session.commit()
    return panel_response("Conta a pagar removida.", {"id": entry_id, "status": "deleted"})


@app.post("/admin/panel/{workspace_slug}/whatsapp/send", status_code=201, tags=["health"])
def admin_panel_send_whatsapp(
    payload: PanelWhatsappSendRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("whatsapp.send")),
) -> dict:
    if payload.client_id is None and payload.lead_id is None:
        raise HTTPException(status_code=422, detail="client_id or lead_id is required.")
    message = Message(
        client_id=payload.client_id,
        lead_id=payload.lead_id,
        direction="outbound",
        body=payload.body,
        status="sending",
    )
    session.add(message)
    session.commit()
    session.refresh(message)
    return panel_response("Mensagem enviada para fila imediata.", {"message_id": message.id, "status": message.status})
