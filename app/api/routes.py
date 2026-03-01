from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import (
    central_current_user_dep,
    central_session_dep,
    tenant_admin_user_dep,
    tenant_context_dep,
    tenant_current_user_dep,
    tenant_session_dep,
)
from app.core.security import build_token, verify_password
from app.models.central import CentralUser, Tenant
from app.models.tenant import (
    AccountsPayable,
    AccountsReceivable,
    Client,
    Contract,
    Lead,
    Message,
    Proposal,
    SalesItem,
    SalesOrder,
    TenantWhatsappAccount,
    User,
    WhatsappUnmatchedInbox,
)
from app.schemas.auth import (
    CentralUserResponse,
    LoginRequest,
    RefreshRequest,
    TenantLoginRequest,
    TenantRefreshRequest,
    TokenResponse,
)
from app.schemas.crm import (
    AccountEntryCreateRequest,
    AccountEntryResponse,
    AccountEntryUpdateRequest,
    ClientCreateRequest,
    ClientResponse,
    ClientUpdateRequest,
    ContractUpdateRequest,
    LeadConversionRequest,
    LeadCreateRequest,
    LeadResponse,
    LeadUpdateRequest,
    ContractCreateRequest,
    ContractResponse,
    ProposalCreateRequest,
    ProposalResponse,
    ProposalUpdateRequest,
    SalesItemCreateRequest,
    SalesItemResponse,
    SalesOrderCreateRequest,
    SalesOrderResponse,
    SalesOrderUpdateRequest,
    TenantUserCreateRequest,
    TenantUserResponse,
    TenantUserUpdateRequest,
    WhatsappInboundRequest,
    WhatsappSessionRequest,
    WhatsappSessionResponse,
    WhatsappUnmatchedResponse,
)
from app.schemas.tenant import TenantCreateRequest, TenantCreateResponse
from app.services.auth import issue_token_pair, persist_refresh_token, rotate_refresh_token
from app.services.tenant_auth import (
    issue_tenant_token_pair,
    persist_tenant_refresh_token,
    revoke_tenant_refresh_token,
    rotate_tenant_refresh_token,
)
from app.services.tenants import create_tenant


def _write_document_file(workspace_slug: str, doc_type: str, entity_id: int, title: str) -> str:
    from pathlib import Path

    from app.core.config import DATA_DIR

    target_dir = Path(DATA_DIR / "generated" / workspace_slug / doc_type)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{entity_id}.pdf"
    content = (
        "%PDF-1.1\n"
        "1 0 obj<<>>endobj\n"
        "2 0 obj<< /Length 44 >>stream\n"
        f"{doc_type.upper()} #{entity_id} - {title}\n"
        "endstream\nendobj\n"
        "trailer<<>>\n%%EOF\n"
    )
    target_file.write_text(content, encoding="utf-8")
    return target_file.as_posix()


router = APIRouter()


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/central/auth/login", response_model=TokenResponse)
def central_login(payload: LoginRequest, session: Session = Depends(central_session_dep)) -> TokenResponse:
    user = session.query(CentralUser).filter(CentralUser.email == payload.email).one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    access_token, refresh_token = issue_token_pair(user.email)
    persist_refresh_token(session, refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/central/auth/refresh", response_model=TokenResponse)
def central_refresh(payload: RefreshRequest, session: Session = Depends(central_session_dep)) -> TokenResponse:
    try:
        access_token, refresh_token = rotate_refresh_token(session, payload.refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token.")
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/central/auth/me", response_model=CentralUserResponse)
def central_me(current_user: CentralUser = Depends(central_current_user_dep)) -> CentralUserResponse:
    return CentralUserResponse(
        email=current_user.email,
        full_name=current_user.full_name,
        must_change_password=current_user.must_change_password,
    )


@router.post("/tenant/{workspace_slug}/auth/login", response_model=TokenResponse)
def tenant_login(
    payload: TenantLoginRequest,
    session: Session = Depends(tenant_session_dep),
) -> TokenResponse:
    user = session.query(User).filter(User.email == payload.email).one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    access_token, refresh_token = issue_tenant_token_pair(
        user.email, is_admin=user.is_admin, must_change_password=user.must_change_password
    )
    persist_tenant_refresh_token(session, refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/tenant/{workspace_slug}/auth/refresh", response_model=TokenResponse)
def tenant_refresh(
    payload: TenantRefreshRequest,
    session: Session = Depends(tenant_session_dep),
) -> TokenResponse:
    from app.core.security import decode_token

    try:
        current = decode_token(payload.refresh_token)
        user = session.query(User).filter(User.email == current["sub"]).one_or_none()
        if user is None:
            raise ValueError
        access_token, refresh_token = rotate_tenant_refresh_token(session, payload.refresh_token, is_admin=user.is_admin)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token.")
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/tenant/{workspace_slug}/auth/logout", status_code=204)
def tenant_logout(
    payload: TenantRefreshRequest,
    session: Session = Depends(tenant_session_dep),
) -> None:
    try:
        revoke_tenant_refresh_token(session, payload.refresh_token)
    except ValueError:
        pass


@router.post("/central/tenants", response_model=TenantCreateResponse, status_code=201)
def central_create_tenant(
    payload: TenantCreateRequest,
    session: Session = Depends(central_session_dep),
    _: CentralUser = Depends(central_current_user_dep),
) -> TenantCreateResponse:
    existing = session.query(Tenant).filter(Tenant.slug == payload.workspace_slug).one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Workspace slug already exists.")

    tenant = create_tenant(session, payload, actor_email="admin@mayacorp.com")
    return TenantCreateResponse(
        tenant_id=tenant.id,
        tenant_db_url=tenant.database_url,
        message="Tenant created with isolated database.",
    )


@router.get("/tenant/{workspace_slug}/context")
def tenant_context(tenant: Tenant = Depends(tenant_context_dep)) -> dict[str, str]:
    return {"workspace": tenant.slug, "status": tenant.status, "plan": tenant.plan_code}


@router.get("/tenant/{workspace_slug}/users", response_model=list[TenantUserResponse])
def list_tenant_users(session: Session = Depends(tenant_session_dep)) -> list[TenantUserResponse]:
    users = session.query(User).order_by(User.id.asc()).all()
    return [
        TenantUserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_admin=user.is_admin,
            must_change_password=user.must_change_password,
        )
        for user in users
    ]


@router.post("/tenant/{workspace_slug}/users", response_model=TenantUserResponse, status_code=201)
def create_tenant_user(
    payload: TenantUserCreateRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_admin_user_dep),
) -> TenantUserResponse:
    existing = session.query(User).filter(User.email == payload.email).one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="User email already exists.")

    from app.core.security import hash_password

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        is_admin=payload.is_admin,
        must_change_password=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return TenantUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin,
        must_change_password=user.must_change_password,
    )


@router.patch("/tenant/{workspace_slug}/users/{user_id}", response_model=TenantUserResponse)
def update_tenant_user(
    user_id: int,
    payload: TenantUserUpdateRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_admin_user_dep),
) -> TenantUserResponse:
    user = session.query(User).filter(User.id == user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    if payload.is_active is not None:
        user.is_active = payload.is_active
    session.commit()
    session.refresh(user)
    return TenantUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin,
        must_change_password=user.must_change_password,
    )


@router.delete("/tenant/{workspace_slug}/users/{user_id}", status_code=204)
def delete_tenant_user(
    user_id: int, session: Session = Depends(tenant_session_dep), _: User = Depends(tenant_admin_user_dep)
) -> None:
    user = session.query(User).filter(User.id == user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    session.delete(user)
    session.commit()


@router.get("/tenant/{workspace_slug}/leads", response_model=list[LeadResponse])
def list_leads(session: Session = Depends(tenant_session_dep)) -> list[LeadResponse]:
    leads = session.query(Lead).order_by(Lead.id.desc()).all()
    return [
        LeadResponse(
            id=lead.id,
            name=lead.name,
            email=lead.email,
            phone=lead.phone,
            source=lead.source,
            manual_classification=lead.manual_classification,
            conversion_date=lead.conversion_date,
        )
        for lead in leads
    ]


@router.post("/tenant/{workspace_slug}/leads", response_model=LeadResponse, status_code=201)
def create_lead(payload: LeadCreateRequest, session: Session = Depends(tenant_session_dep)) -> LeadResponse:
    lead = Lead(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        source=payload.source,
        manual_classification=payload.manual_classification,
    )
    session.add(lead)
    session.commit()
    session.refresh(lead)
    return LeadResponse(
        id=lead.id,
        name=lead.name,
        email=lead.email,
        phone=lead.phone,
        source=lead.source,
        manual_classification=lead.manual_classification,
        conversion_date=lead.conversion_date,
    )


@router.patch("/tenant/{workspace_slug}/leads/{lead_id}", response_model=LeadResponse)
def update_lead(lead_id: int, payload: LeadUpdateRequest, session: Session = Depends(tenant_session_dep)) -> LeadResponse:
    lead = session.query(Lead).filter(Lead.id == lead_id).one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    for field in ("name", "email", "phone", "source", "manual_classification"):
        value = getattr(payload, field)
        if value is not None:
            setattr(lead, field, value)
    session.commit()
    session.refresh(lead)
    return LeadResponse(
        id=lead.id,
        name=lead.name,
        email=lead.email,
        phone=lead.phone,
        source=lead.source,
        manual_classification=lead.manual_classification,
        conversion_date=lead.conversion_date,
    )


@router.delete("/tenant/{workspace_slug}/leads/{lead_id}", status_code=204)
def delete_lead(lead_id: int, session: Session = Depends(tenant_session_dep)) -> None:
    lead = session.query(Lead).filter(Lead.id == lead_id).one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    session.delete(lead)
    session.commit()


@router.post("/tenant/{workspace_slug}/clients", response_model=ClientResponse, status_code=201)
def create_client(payload: ClientCreateRequest, session: Session = Depends(tenant_session_dep)) -> ClientResponse:
    if payload.source_lead_id is not None:
        lead = session.query(Lead).filter(Lead.id == payload.source_lead_id).one_or_none()
        if lead is None:
            raise HTTPException(status_code=404, detail="Lead not found.")

    client = Client(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        source_lead_id=payload.source_lead_id,
    )
    session.add(client)
    session.commit()
    session.refresh(client)
    return ClientResponse(
        id=client.id,
        name=client.name,
        email=client.email,
        phone=client.phone,
        source_lead_id=client.source_lead_id,
    )


@router.post("/tenant/{workspace_slug}/leads/{lead_id}/convert", response_model=ClientResponse, status_code=201)
def convert_lead(
    lead_id: int, payload: LeadConversionRequest, session: Session = Depends(tenant_session_dep)
) -> ClientResponse:
    from datetime import UTC, datetime

    lead = session.query(Lead).filter(Lead.id == lead_id).one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found.")

    client = Client(
        name=payload.client_name or lead.name,
        email=payload.client_email or lead.email,
        phone=payload.client_phone or lead.phone,
        source_lead_id=lead.id,
    )
    lead.conversion_date = datetime.now(UTC)
    session.add(client)
    session.commit()
    session.refresh(client)
    return ClientResponse(
        id=client.id,
        name=client.name,
        email=client.email,
        phone=client.phone,
        source_lead_id=client.source_lead_id,
    )


@router.get("/tenant/{workspace_slug}/clients", response_model=list[ClientResponse])
def list_clients(session: Session = Depends(tenant_session_dep)) -> list[ClientResponse]:
    clients = session.query(Client).order_by(Client.id.desc()).all()
    return [
        ClientResponse(
            id=client.id,
            name=client.name,
            email=client.email,
            phone=client.phone,
            source_lead_id=client.source_lead_id,
        )
        for client in clients
    ]


@router.patch("/tenant/{workspace_slug}/clients/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int, payload: ClientUpdateRequest, session: Session = Depends(tenant_session_dep)
) -> ClientResponse:
    client = session.query(Client).filter(Client.id == client_id).one_or_none()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found.")
    for field in ("name", "email", "phone"):
        value = getattr(payload, field)
        if value is not None:
            setattr(client, field, value)
    session.commit()
    session.refresh(client)
    return ClientResponse(
        id=client.id,
        name=client.name,
        email=client.email,
        phone=client.phone,
        source_lead_id=client.source_lead_id,
    )


@router.delete("/tenant/{workspace_slug}/clients/{client_id}", status_code=204)
def delete_client(client_id: int, session: Session = Depends(tenant_session_dep)) -> None:
    client = session.query(Client).filter(Client.id == client_id).one_or_none()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found.")
    session.delete(client)
    session.commit()


@router.post("/tenant/{workspace_slug}/finance/accounts-receivable", response_model=AccountEntryResponse, status_code=201)
def create_account_receivable(
    payload: AccountEntryCreateRequest, session: Session = Depends(tenant_session_dep)
) -> AccountEntryResponse:
    from datetime import date

    entry = AccountsReceivable(
        amount=payload.amount,
        due_date=date.fromisoformat(payload.due_date),
        category=payload.category,
        cost_center=payload.cost_center,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return AccountEntryResponse(
        id=entry.id,
        amount=float(entry.amount),
        due_date=entry.due_date.isoformat(),
        status=entry.status,
        category=entry.category,
        cost_center=entry.cost_center,
    )


@router.get("/tenant/{workspace_slug}/finance/accounts-receivable", response_model=list[AccountEntryResponse])
def list_accounts_receivable(
    due_date_from: str | None = None,
    due_date_to: str | None = None,
    category: str | None = None,
    cost_center: str | None = None,
    session: Session = Depends(tenant_session_dep),
) -> list[AccountEntryResponse]:
    from datetime import date

    query = session.query(AccountsReceivable)
    if due_date_from:
        query = query.filter(AccountsReceivable.due_date >= date.fromisoformat(due_date_from))
    if due_date_to:
        query = query.filter(AccountsReceivable.due_date <= date.fromisoformat(due_date_to))
    if category:
        query = query.filter(AccountsReceivable.category == category)
    if cost_center:
        query = query.filter(AccountsReceivable.cost_center == cost_center)
    entries = query.order_by(AccountsReceivable.id.desc()).all()
    return [
        AccountEntryResponse(
            id=entry.id,
            amount=float(entry.amount),
            due_date=entry.due_date.isoformat(),
            status=entry.status,
            category=entry.category,
            cost_center=entry.cost_center,
        )
        for entry in entries
    ]


@router.patch(
    "/tenant/{workspace_slug}/finance/accounts-receivable/{entry_id}",
    response_model=AccountEntryResponse,
)
def update_account_receivable(
    entry_id: int, payload: AccountEntryUpdateRequest, session: Session = Depends(tenant_session_dep)
) -> AccountEntryResponse:
    from datetime import date

    entry = session.query(AccountsReceivable).filter(AccountsReceivable.id == entry_id).one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Accounts receivable entry not found.")
    if payload.amount is not None:
        entry.amount = payload.amount
    if payload.due_date is not None:
        entry.due_date = date.fromisoformat(payload.due_date)
    if payload.status is not None:
        entry.status = payload.status
    if payload.category is not None:
        entry.category = payload.category
    if payload.cost_center is not None:
        entry.cost_center = payload.cost_center
    session.commit()
    session.refresh(entry)
    return AccountEntryResponse(
        id=entry.id,
        amount=float(entry.amount),
        due_date=entry.due_date.isoformat(),
        status=entry.status,
        category=entry.category,
        cost_center=entry.cost_center,
    )


@router.delete("/tenant/{workspace_slug}/finance/accounts-receivable/{entry_id}", status_code=204)
def delete_account_receivable(entry_id: int, session: Session = Depends(tenant_session_dep)) -> None:
    entry = session.query(AccountsReceivable).filter(AccountsReceivable.id == entry_id).one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Accounts receivable entry not found.")
    session.delete(entry)
    session.commit()


@router.post("/tenant/{workspace_slug}/finance/accounts-payable", response_model=AccountEntryResponse, status_code=201)
def create_account_payable(
    payload: AccountEntryCreateRequest, session: Session = Depends(tenant_session_dep)
) -> AccountEntryResponse:
    from datetime import date

    entry = AccountsPayable(
        amount=payload.amount,
        due_date=date.fromisoformat(payload.due_date),
        category=payload.category,
        cost_center=payload.cost_center,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return AccountEntryResponse(
        id=entry.id,
        amount=float(entry.amount),
        due_date=entry.due_date.isoformat(),
        status=entry.status,
        category=entry.category,
        cost_center=entry.cost_center,
    )


@router.get("/tenant/{workspace_slug}/finance/accounts-payable", response_model=list[AccountEntryResponse])
def list_accounts_payable(
    due_date_from: str | None = None,
    due_date_to: str | None = None,
    category: str | None = None,
    cost_center: str | None = None,
    session: Session = Depends(tenant_session_dep),
) -> list[AccountEntryResponse]:
    from datetime import date

    query = session.query(AccountsPayable)
    if due_date_from:
        query = query.filter(AccountsPayable.due_date >= date.fromisoformat(due_date_from))
    if due_date_to:
        query = query.filter(AccountsPayable.due_date <= date.fromisoformat(due_date_to))
    if category:
        query = query.filter(AccountsPayable.category == category)
    if cost_center:
        query = query.filter(AccountsPayable.cost_center == cost_center)
    entries = query.order_by(AccountsPayable.id.desc()).all()
    return [
        AccountEntryResponse(
            id=entry.id,
            amount=float(entry.amount),
            due_date=entry.due_date.isoformat(),
            status=entry.status,
            category=entry.category,
            cost_center=entry.cost_center,
        )
        for entry in entries
    ]


@router.patch("/tenant/{workspace_slug}/finance/accounts-payable/{entry_id}", response_model=AccountEntryResponse)
def update_account_payable(
    entry_id: int, payload: AccountEntryUpdateRequest, session: Session = Depends(tenant_session_dep)
) -> AccountEntryResponse:
    from datetime import date

    entry = session.query(AccountsPayable).filter(AccountsPayable.id == entry_id).one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Accounts payable entry not found.")
    if payload.amount is not None:
        entry.amount = payload.amount
    if payload.due_date is not None:
        entry.due_date = date.fromisoformat(payload.due_date)
    if payload.status is not None:
        entry.status = payload.status
    if payload.category is not None:
        entry.category = payload.category
    if payload.cost_center is not None:
        entry.cost_center = payload.cost_center
    session.commit()
    session.refresh(entry)
    return AccountEntryResponse(
        id=entry.id,
        amount=float(entry.amount),
        due_date=entry.due_date.isoformat(),
        status=entry.status,
        category=entry.category,
        cost_center=entry.cost_center,
    )


@router.delete("/tenant/{workspace_slug}/finance/accounts-payable/{entry_id}", status_code=204)
def delete_account_payable(entry_id: int, session: Session = Depends(tenant_session_dep)) -> None:
    entry = session.query(AccountsPayable).filter(AccountsPayable.id == entry_id).one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Accounts payable entry not found.")
    session.delete(entry)
    session.commit()


@router.post("/tenant/{workspace_slug}/sales-orders", response_model=SalesOrderResponse, status_code=201)
def create_sales_order(
    payload: SalesOrderCreateRequest, session: Session = Depends(tenant_session_dep)
) -> SalesOrderResponse:
    from datetime import date
    from decimal import Decimal

    if payload.client_id is not None:
        client = session.query(Client).filter(Client.id == payload.client_id).one_or_none()
        if client is None:
            raise HTTPException(status_code=404, detail="Client not found.")

    if not hasattr(payload, "items") or not payload.items:
        raise HTTPException(status_code=422, detail="At least one sales item is required.")

    total_amount = sum(Decimal(str(item.quantity)) * Decimal(str(item.unit_price)) for item in payload.items)

    order = SalesOrder(
        client_id=payload.client_id,
        order_type=payload.order_type,
        duration_months=payload.duration_months,
        total_amount=total_amount,
        status="confirmed",
    )
    session.add(order)
    session.flush()

    for item in payload.items:
        session.add(
            SalesItem(
                sales_order_id=order.id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
        )

    installment_amount = (total_amount / Decimal(payload.installments)).quantize(Decimal("0.01"))
    first_due = date.fromisoformat(payload.first_due_date)

    for index in range(payload.installments):
        due_month = first_due.month - 1 + index
        due_year = first_due.year + due_month // 12
        due_month_normalized = due_month % 12 + 1
        due_date = date(due_year, due_month_normalized, min(first_due.day, 28))
        session.add(
            AccountsReceivable(
                sales_order_id=order.id,
                due_date=due_date,
                amount=installment_amount,
                status="pending",
                category=payload.category,
                cost_center=payload.cost_center,
            )
        )

    session.commit()
    session.refresh(order)
    return SalesOrderResponse(
        id=order.id,
        client_id=order.client_id,
        order_type=order.order_type,
        duration_months=order.duration_months,
        total_amount=float(order.total_amount),
        status=order.status,
    )


@router.get("/tenant/{workspace_slug}/sales-orders/{order_id}/items", response_model=list[SalesItemResponse])
def list_sales_order_items(order_id: int, session: Session = Depends(tenant_session_dep)) -> list[SalesItemResponse]:
    items = session.query(SalesItem).filter(SalesItem.sales_order_id == order_id).order_by(SalesItem.id.asc()).all()
    return [
        SalesItemResponse(
            id=item.id,
            description=item.description,
            quantity=float(item.quantity),
            unit_price=float(item.unit_price),
        )
        for item in items
    ]


@router.get("/tenant/{workspace_slug}/sales-orders", response_model=list[SalesOrderResponse])
def list_sales_orders(session: Session = Depends(tenant_session_dep)) -> list[SalesOrderResponse]:
    orders = session.query(SalesOrder).order_by(SalesOrder.id.desc()).all()
    return [
        SalesOrderResponse(
            id=order.id,
            client_id=order.client_id,
            order_type=order.order_type,
            duration_months=order.duration_months,
            total_amount=float(order.total_amount),
            status=order.status,
        )
        for order in orders
    ]


@router.patch("/tenant/{workspace_slug}/sales-orders/{order_id}", response_model=SalesOrderResponse)
def update_sales_order(
    order_id: int, payload: SalesOrderUpdateRequest, session: Session = Depends(tenant_session_dep)
) -> SalesOrderResponse:
    order = session.query(SalesOrder).filter(SalesOrder.id == order_id).one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Sales order not found.")
    if payload.status is not None:
        order.status = payload.status
    if payload.order_type is not None:
        order.order_type = payload.order_type
    if payload.duration_months is not None:
        order.duration_months = payload.duration_months
    session.commit()
    session.refresh(order)
    return SalesOrderResponse(
        id=order.id,
        client_id=order.client_id,
        order_type=order.order_type,
        duration_months=order.duration_months,
        total_amount=float(order.total_amount),
        status=order.status,
    )


@router.delete("/tenant/{workspace_slug}/sales-orders/{order_id}", status_code=204)
def delete_sales_order(order_id: int, session: Session = Depends(tenant_session_dep)) -> None:
    order = session.query(SalesOrder).filter(SalesOrder.id == order_id).one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Sales order not found.")
    session.query(SalesItem).filter(SalesItem.sales_order_id == order.id).delete()
    session.query(AccountsReceivable).filter(AccountsReceivable.sales_order_id == order.id).delete()
    session.delete(order)
    session.commit()


@router.post("/tenant/{workspace_slug}/proposals", response_model=ProposalResponse, status_code=201)
def create_proposal(
    workspace_slug: str,
    payload: ProposalCreateRequest,
    session: Session = Depends(tenant_session_dep),
) -> ProposalResponse:
    if payload.client_id is not None:
        client = session.query(Client).filter(Client.id == payload.client_id).one_or_none()
        if client is None:
            raise HTTPException(status_code=404, detail="Client not found.")
    proposal = Proposal(
        client_id=payload.client_id,
        title=payload.title,
        template_name=payload.template_name,
        is_sendable=payload.is_sendable,
    )
    session.add(proposal)
    session.commit()
    session.refresh(proposal)
    proposal.pdf_path = _write_document_file(workspace_slug, "proposals", proposal.id, proposal.title)
    session.commit()
    session.refresh(proposal)
    return ProposalResponse(
        id=proposal.id,
        client_id=proposal.client_id,
        title=proposal.title,
        template_name=proposal.template_name,
        pdf_path=proposal.pdf_path,
        is_sendable=proposal.is_sendable,
    )


@router.get("/tenant/{workspace_slug}/proposals", response_model=list[ProposalResponse])
def list_proposals(session: Session = Depends(tenant_session_dep)) -> list[ProposalResponse]:
    proposals = session.query(Proposal).order_by(Proposal.id.desc()).all()
    return [
        ProposalResponse(
            id=proposal.id,
            client_id=proposal.client_id,
            title=proposal.title,
            template_name=proposal.template_name,
            pdf_path=proposal.pdf_path,
            is_sendable=proposal.is_sendable,
        )
        for proposal in proposals
    ]


@router.patch("/tenant/{workspace_slug}/proposals/{proposal_id}", response_model=ProposalResponse)
def update_proposal(
    workspace_slug: str,
    proposal_id: int,
    payload: ProposalUpdateRequest,
    session: Session = Depends(tenant_session_dep),
) -> ProposalResponse:
    proposal = session.query(Proposal).filter(Proposal.id == proposal_id).one_or_none()
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found.")
    if payload.title is not None:
        proposal.title = payload.title
    if payload.template_name is not None:
        proposal.template_name = payload.template_name
    if payload.is_sendable is not None:
        proposal.is_sendable = payload.is_sendable
    proposal.pdf_path = _write_document_file(workspace_slug, "proposals", proposal.id, proposal.title)
    session.commit()
    session.refresh(proposal)
    return ProposalResponse(
        id=proposal.id,
        client_id=proposal.client_id,
        title=proposal.title,
        template_name=proposal.template_name,
        pdf_path=proposal.pdf_path,
        is_sendable=proposal.is_sendable,
    )


@router.delete("/tenant/{workspace_slug}/proposals/{proposal_id}", status_code=204)
def delete_proposal(proposal_id: int, session: Session = Depends(tenant_session_dep)) -> None:
    proposal = session.query(Proposal).filter(Proposal.id == proposal_id).one_or_none()
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found.")
    session.delete(proposal)
    session.commit()


@router.post("/tenant/{workspace_slug}/contracts", response_model=ContractResponse, status_code=201)
def create_contract(
    workspace_slug: str,
    payload: ContractCreateRequest,
    session: Session = Depends(tenant_session_dep),
) -> ContractResponse:
    if payload.client_id is not None:
        client = session.query(Client).filter(Client.id == payload.client_id).one_or_none()
        if client is None:
            raise HTTPException(status_code=404, detail="Client not found.")
    contract = Contract(
        client_id=payload.client_id,
        title=payload.title,
        template_name=payload.template_name,
    )
    session.add(contract)
    session.commit()
    session.refresh(contract)
    contract.pdf_path = _write_document_file(workspace_slug, "contracts", contract.id, contract.title)
    session.commit()
    session.refresh(contract)
    return ContractResponse(
        id=contract.id,
        client_id=contract.client_id,
        title=contract.title,
        template_name=contract.template_name,
        pdf_path=contract.pdf_path,
        signed_file_path=contract.signed_file_path,
    )


@router.get("/tenant/{workspace_slug}/contracts", response_model=list[ContractResponse])
def list_contracts(session: Session = Depends(tenant_session_dep)) -> list[ContractResponse]:
    contracts = session.query(Contract).order_by(Contract.id.desc()).all()
    return [
        ContractResponse(
            id=contract.id,
            client_id=contract.client_id,
            title=contract.title,
            template_name=contract.template_name,
            pdf_path=contract.pdf_path,
            signed_file_path=contract.signed_file_path,
        )
        for contract in contracts
    ]


@router.patch("/tenant/{workspace_slug}/contracts/{contract_id}", response_model=ContractResponse)
def update_contract(
    workspace_slug: str,
    contract_id: int,
    payload: ContractUpdateRequest,
    session: Session = Depends(tenant_session_dep),
) -> ContractResponse:
    contract = session.query(Contract).filter(Contract.id == contract_id).one_or_none()
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found.")
    if payload.title is not None:
        contract.title = payload.title
    if payload.template_name is not None:
        contract.template_name = payload.template_name
    contract.pdf_path = _write_document_file(workspace_slug, "contracts", contract.id, contract.title)
    session.commit()
    session.refresh(contract)
    return ContractResponse(
        id=contract.id,
        client_id=contract.client_id,
        title=contract.title,
        template_name=contract.template_name,
        pdf_path=contract.pdf_path,
        signed_file_path=contract.signed_file_path,
    )


@router.delete("/tenant/{workspace_slug}/contracts/{contract_id}", status_code=204)
def delete_contract(contract_id: int, session: Session = Depends(tenant_session_dep)) -> None:
    contract = session.query(Contract).filter(Contract.id == contract_id).one_or_none()
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found.")
    session.delete(contract)
    session.commit()


@router.post("/tenant/{workspace_slug}/whatsapp/session", response_model=WhatsappSessionResponse, status_code=201)
def upsert_whatsapp_session(
    payload: WhatsappSessionRequest, session: Session = Depends(tenant_session_dep)
) -> WhatsappSessionResponse:
    account = session.query(TenantWhatsappAccount).order_by(TenantWhatsappAccount.id.asc()).first()
    if account is None:
        account = TenantWhatsappAccount(
            provider_session_id=payload.provider_session_id,
            status="connecting",
            last_qr_code="qr-placeholder",
        )
        session.add(account)
    else:
        account.provider_session_id = payload.provider_session_id
        account.status = "connecting"
        account.last_qr_code = "qr-placeholder"
    session.commit()
    session.refresh(account)
    return WhatsappSessionResponse(
        id=account.id,
        provider_session_id=account.provider_session_id,
        status=account.status,
        last_qr_code=account.last_qr_code,
    )


@router.get("/tenant/{workspace_slug}/whatsapp/session", response_model=WhatsappSessionResponse | None)
def get_whatsapp_session(session: Session = Depends(tenant_session_dep)) -> WhatsappSessionResponse | None:
    account = session.query(TenantWhatsappAccount).order_by(TenantWhatsappAccount.id.asc()).first()
    if account is None:
        return None
    return WhatsappSessionResponse(
        id=account.id,
        provider_session_id=account.provider_session_id,
        status=account.status,
        last_qr_code=account.last_qr_code,
    )


@router.post("/tenant/{workspace_slug}/whatsapp/inbound", status_code=201)
def whatsapp_inbound(
    payload: WhatsappInboundRequest, session: Session = Depends(tenant_session_dep)
) -> dict[str, str]:
    resolved_client_id = payload.client_id
    resolved_lead_id = payload.lead_id

    if resolved_client_id is None and resolved_lead_id is None:
        client = session.query(Client).filter(Client.phone == payload.external_sender).one_or_none()
        if client is not None:
            resolved_client_id = client.id
        else:
            lead = session.query(Lead).filter(Lead.phone == payload.external_sender).one_or_none()
            if lead is not None:
                resolved_lead_id = lead.id

    if resolved_client_id is not None or resolved_lead_id is not None:
        message = Message(
            client_id=resolved_client_id,
            lead_id=resolved_lead_id,
            direction="inbound",
            body=payload.body,
            status="read",
        )
        session.add(message)
        session.commit()
        return {"status": "matched"}

    unmatched = WhatsappUnmatchedInbox(
        external_sender=payload.external_sender,
        body=payload.body,
        matched=False,
    )
    session.add(unmatched)
    session.commit()
    return {"status": "unmatched"}


@router.get("/tenant/{workspace_slug}/whatsapp/unmatched-inbox", response_model=list[WhatsappUnmatchedResponse])
def list_unmatched_inbox(session: Session = Depends(tenant_session_dep)) -> list[WhatsappUnmatchedResponse]:
    items = session.query(WhatsappUnmatchedInbox).order_by(WhatsappUnmatchedInbox.id.desc()).all()
    return [
        WhatsappUnmatchedResponse(
            id=item.id,
            external_sender=item.external_sender,
            body=item.body,
            matched=item.matched,
        )
        for item in items
    ]
