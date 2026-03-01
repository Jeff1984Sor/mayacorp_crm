from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import central_current_user_dep, central_session_dep, tenant_context_dep, tenant_session_dep
from app.core.security import build_token, verify_password
from app.models.central import CentralUser, Tenant
from app.models.tenant import Client, Lead, User
from app.schemas.auth import CentralUserResponse, LoginRequest, TokenResponse
from app.schemas.crm import (
    ClientCreateRequest,
    ClientResponse,
    LeadCreateRequest,
    LeadResponse,
    TenantUserCreateRequest,
    TenantUserResponse,
)
from app.schemas.tenant import TenantCreateRequest, TenantCreateResponse
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

    token = build_token(user.email, extra={"scope": "central", "must_change_password": user.must_change_password})
    return TokenResponse(access_token=token)


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
