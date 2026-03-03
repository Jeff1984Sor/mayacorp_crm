from __future__ import annotations

from fastapi import Cookie, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.api.deps import central_session_dep, tenant_context_dep, tenant_session_dep
from app.core.security import decode_token
from app.models.central import CentralUser, Tenant
from app.models.tenant import User

PANEL_ORDER_STATUSES = {"pending", "confirmed", "closed", "cancelled"}
PANEL_FINANCE_STATUSES = {"pending", "paid", "overdue", "cancelled"}
PANEL_WHATSAPP_SESSION_STATUSES = {"connecting", "connected", "disconnected", "failed"}
PANEL_MESSAGE_STATUSES = {"sending", "sent", "delivered", "read", "failed"}
PANEL_CONTRACT_STATUSES = {"draft", "sent", "signed", "cancelled"}


class PanelCentralLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4, max_length=128)


class PanelTenantLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4, max_length=128)


class PanelTenantCreateRequest(BaseModel):
    account_id: int | None = None
    company_name: str = Field(min_length=2, max_length=255)
    workspace_slug: str = Field(min_length=2, max_length=80)
    account_stage: str = Field(default="lead", max_length=40)
    admin_name: str = Field(min_length=2, max_length=255)
    admin_email: EmailStr
    admin_password: str = Field(min_length=4, max_length=128)


class PanelSalesOrderRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    quantity: float = Field(default=1, gt=0)
    unit_price: float = Field(gt=0)
    first_due_date: str
    company_account_id: int | None = None


class PanelSalesOrderEditRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    quantity: float = Field(default=1, gt=0)
    unit_price: float = Field(gt=0)
    first_due_date: str


class PanelProposalRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    sales_order_id: int | None = None
    company_account_id: int | None = None


class PanelContractRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    sales_order_id: int | None = None
    company_account_id: int | None = None


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
    company_account_id: int | None = None


class PanelClientRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    company_account_id: int | None = None


class PanelCompanyAccountRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    lifecycle_stage: str = Field(default="lead", max_length=40)
    admin_email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    company_document: str | None = Field(default=None, max_length=40)
    notes: str | None = None


class PanelStatusRequest(BaseModel):
    status: str = Field(min_length=2, max_length=40)


class PanelFinanceEntryRequest(BaseModel):
    amount: float = Field(gt=0)
    due_date: str
    category: str | None = Field(default=None, max_length=80)
    cost_center: str | None = Field(default=None, max_length=80)
    status: str = Field(default="pending", max_length=40)


class PanelFinanceReconcileRequest(BaseModel):
    status: str | None = Field(default=None, max_length=40)
    category: str | None = Field(default=None, max_length=80)
    due_from: str | None = None
    due_to: str | None = None


class PanelWhatsappSendRequest(BaseModel):
    body: str = Field(min_length=1)
    lead_id: int | None = None
    client_id: int | None = None


def panel_cookie_options() -> dict:
    return {
        "httponly": True,
        "samesite": "lax",
        "secure": False,
        "max_age": 3600,
    }


def panel_response(message: str, data: dict | list | None = None, ok: bool = True) -> dict:
    return {"ok": ok, "message": message, "data": data}


def ensure_panel_status(status: str, allowed: set[str], context: str) -> str:
    if status not in allowed:
        raise HTTPException(status_code=422, detail=f"Invalid {context} status: {status}")
    return status


def panel_central_user_dep(
    panel_central_token: str | None = Cookie(default=None),
    x_panel_central_token: str | None = Header(default=None),
    session: Session = Depends(central_session_dep),
) -> CentralUser:
    token = panel_central_token or x_panel_central_token
    if not token:
        raise HTTPException(status_code=401, detail="Panel central session required.")
    try:
        payload = decode_token(token)
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
    panel_tenant_slug: str | None = Cookie(default=None),
    x_panel_tenant_token: str | None = Header(default=None),
    x_panel_tenant_slug: str | None = Header(default=None),
    tenant: Tenant = Depends(tenant_context_dep),
    session: Session = Depends(tenant_session_dep),
) -> User:
    token = panel_tenant_token or x_panel_tenant_token
    tenant_slug = panel_tenant_slug or x_panel_tenant_slug
    if not token:
        raise HTTPException(status_code=401, detail="Panel tenant session required.")
    if tenant_slug != tenant.slug:
        raise HTTPException(status_code=403, detail="Panel tenant workspace mismatch.")
    try:
        payload = decode_token(token)
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
