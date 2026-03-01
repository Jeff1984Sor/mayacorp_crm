from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import central_session_dep, tenant_context_dep
from app.core.security import build_token, verify_password
from app.models.central import CentralUser, Tenant
from app.schemas.auth import LoginRequest, TokenResponse
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


@router.post("/central/tenants", response_model=TenantCreateResponse, status_code=201)
def central_create_tenant(
    payload: TenantCreateRequest,
    session: Session = Depends(central_session_dep),
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
