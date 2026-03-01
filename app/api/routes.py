from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import central_current_user_dep, central_session_dep, tenant_context_dep, tenant_session_dep
from app.core.security import verify_password
from app.models.central import CentralUser, Tenant
from app.models.tenant import Client, Lead, User
from app.models.tenant import AccountsPayable, AccountsReceivable
from app.schemas.auth import CentralUserResponse, LoginRequest, RefreshRequest, TokenResponse
from app.schemas.crm import (
    AccountEntryCreateRequest,
    AccountEntryResponse,
    ClientCreateRequest,
    ClientResponse,
    ClientUpdateRequest,
    LeadConversionRequest,
    LeadCreateRequest,
    LeadResponse,
    LeadUpdateRequest,
    TenantUserCreateRequest,
    TenantUserResponse,
    TenantUserUpdateRequest,
)
from app.schemas.tenant import TenantCreateRequest, TenantCreateResponse
from app.services.auth import issue_token_pair, persist_refresh_token, rotate_refresh_token
from app.services.tenants import create_tenant


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
def create_tenant_user(payload: TenantUserCreateRequest, session: Session = Depends(tenant_session_dep)) -> TenantUserResponse:
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
    user_id: int, payload: TenantUserUpdateRequest, session: Session = Depends(tenant_session_dep)
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
def delete_tenant_user(user_id: int, session: Session = Depends(tenant_session_dep)) -> None:
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
def list_accounts_receivable(session: Session = Depends(tenant_session_dep)) -> list[AccountEntryResponse]:
    entries = session.query(AccountsReceivable).order_by(AccountsReceivable.id.desc()).all()
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
def list_accounts_payable(session: Session = Depends(tenant_session_dep)) -> list[AccountEntryResponse]:
    entries = session.query(AccountsPayable).order_by(AccountsPayable.id.desc()).all()
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
