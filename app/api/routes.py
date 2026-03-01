from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import (
    central_current_user_dep,
    central_session_dep,
    tenant_admin_user_dep,
    tenant_manager_user_dep,
    tenant_permission_dep,
    tenant_context_dep,
    tenant_current_user_dep,
    tenant_session_dep,
)
from app.core.security import build_token, decrypt_value, encrypt_value, hash_password, verify_password
from app.models.central import (
    CentralAiSetting,
    CentralRefreshToken,
    SaasInvoice,
    CentralTask,
    TenantAnalyticsSnapshot,
    CentralUser,
    Tenant,
    TenantAiLimit,
    TenantAiUsageDaily,
    TenantHealthScore,
)
from app.models.tenant import (
    AccountsPayable,
    AccountsReceivable,
    Client,
    Contract,
    CostCenter,
    FinanceCategory,
    Lead,
    Message,
    MarketplaceEvent,
    Proposal,
    RoleTemplate,
    SalesItem,
    SalesOrder,
    TenantWhatsappAccount,
    TenantSchemaVersion,
    User,
    WhatsappUnmatchedInbox,
    LeadRadarRun,
)
from app.schemas.auth import (
    CentralUserResponse,
    CentralAiSettingsRequest,
    CentralAiSettingsResponse,
    CentralDashboardResponse,
    CentralPasswordChangeRequest,
    TenantAiGenerateRequest,
    TenantAiGenerateResponse,
    TenantAnalyticsSnapshotResponse,
    TenantAiSummaryResponse,
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
    CostCenterCreateRequest,
    CostCenterResponse,
    CommercialDashboardResponse,
    FinanceCategoryCreateRequest,
    FinanceCategoryResponse,
    FinanceDashboardResponse,
    FinanceExportResponse,
    LeadConversionRequest,
    LeadCreateRequest,
    LeadResponse,
    LeadUpdateRequest,
    ContractCreateRequest,
    ContractResponse,
    ProposalCreateRequest,
    ProposalResponse,
    ProposalUpdateRequest,
    MarketplaceWebhookRequest,
    RoleTemplateUpsertRequest,
    ContractSignedFileRequest,
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
    WhatsappStatusRequest,
    WhatsappOutboundRequest,
    WhatsappUnmatchedResponse,
    LeadRadarCallbackRequest,
    LeadRadarRunCreateRequest,
    LeadRadarRunResponse,
    StorageFileRequest,
    StorageFileResponse,
    StorageResolvedResponse,
    RoleTemplateResponse,
    WorkspaceHealthResponse,
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
from app.services.storage import generate_signed_url, save_workspace_file


def _write_document_file(workspace_slug: str, doc_type: str, entity_id: int, title: str) -> str:
    from pathlib import Path

    from app.core.config import DATA_DIR

    target_dir = Path(DATA_DIR / "generated" / workspace_slug / doc_type)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{entity_id}.pdf"
    sanitized_title = title.replace("(", "[").replace(")", "]")
    stream_content = (
        f"BT /F1 18 Tf 50 780 Td ({doc_type.upper()} #{entity_id}) Tj "
        f"0 -24 Td ({sanitized_title}) Tj 0 -24 Td (Workspace: {workspace_slug}) Tj ET"
    )
    stream_length = len(stream_content.encode("utf-8"))
    content = (
        "%PDF-1.4\n"
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
        "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        f"5 0 obj << /Length {stream_length} >> stream\n{stream_content}\nendstream endobj\n"
        "xref\n0 6\n0000000000 65535 f \n"
        "0000000010 00000 n \n0000000063 00000 n \n0000000122 00000 n \n"
        "0000000248 00000 n \n0000000318 00000 n \n"
        "trailer << /Size 6 /Root 1 0 R >>\nstartxref\n430\n%%EOF\n"
    )
    target_file.write_bytes(content.encode("utf-8"))
    return target_file.as_posix()


def _write_signed_contract_file(workspace_slug: str, contract_id: int, file_name: str, content: str) -> str:
    from pathlib import Path

    from app.core.config import DATA_DIR

    target_dir = Path(DATA_DIR / "generated" / workspace_slug / "contracts" / "signed")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{contract_id}_{Path(file_name).name}"
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


@router.post("/central/auth/change-password", status_code=204)
def central_change_password(
    payload: CentralPasswordChangeRequest,
    session: Session = Depends(central_session_dep),
    current_user: CentralUser = Depends(central_current_user_dep),
) -> None:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is invalid.")
    current_user.password_hash = hash_password(payload.new_password)
    current_user.must_change_password = False
    session.commit()


@router.post("/central/auth/logout-all", status_code=204)
def central_logout_all(
    session: Session = Depends(central_session_dep),
    current_user: CentralUser = Depends(central_current_user_dep),
) -> None:
    from datetime import UTC, datetime

    tokens = session.query(CentralRefreshToken).filter(CentralRefreshToken.user_email == current_user.email).all()
    for token in tokens:
        if token.revoked_at is None:
            token.revoked_at = datetime.now(UTC)
    session.commit()


@router.get("/central/dashboard", response_model=CentralDashboardResponse)
def central_dashboard(
    session: Session = Depends(central_session_dep),
    _: CentralUser = Depends(central_current_user_dep),
) -> CentralDashboardResponse:
    tenants = session.query(Tenant).all()
    invoices = session.query(SaasInvoice).all()
    open_tasks = session.query(CentralTask).filter(CentralTask.status == "open").count()
    return CentralDashboardResponse(
        tenant_count=len(tenants),
        active_tenant_count=sum(1 for tenant in tenants if tenant.status == "active"),
        open_task_count=open_tasks,
        pending_invoice_count=sum(1 for invoice in invoices if invoice.status == "pending"),
        total_invoice_amount=sum(float(invoice.amount) for invoice in invoices),
    )


@router.put("/central/ai/settings", response_model=CentralAiSettingsResponse)
def upsert_central_ai_settings(
    payload: CentralAiSettingsRequest,
    session: Session = Depends(central_session_dep),
    _: CentralUser = Depends(central_current_user_dep),
) -> CentralAiSettingsResponse:
    settings_row = session.query(CentralAiSetting).order_by(CentralAiSetting.id.asc()).first()
    if settings_row is None:
        settings_row = CentralAiSetting()
        session.add(settings_row)
        session.flush()

    settings_row.provider = payload.provider
    settings_row.config = {
        "api_key": encrypt_value(payload.api_key),
        "model_name": payload.model_name,
    }
    session.commit()

    tenants = session.query(Tenant).all()
    for tenant in tenants:
        limit = session.query(TenantAiLimit).filter(TenantAiLimit.tenant_id == tenant.id).one_or_none()
        if limit is None:
            session.add(
                TenantAiLimit(
                    tenant_id=tenant.id,
                    monthly_request_limit=payload.monthly_request_limit,
                    monthly_token_limit=payload.monthly_token_limit,
                )
            )
    session.commit()
    return CentralAiSettingsResponse(
        provider=settings_row.provider,
        model_name=settings_row.config.get("model_name"),
        monthly_request_limit=payload.monthly_request_limit,
        monthly_token_limit=payload.monthly_token_limit,
    )


@router.get("/central/ai/settings", response_model=CentralAiSettingsResponse | None)
def get_central_ai_settings(
    session: Session = Depends(central_session_dep),
    _: CentralUser = Depends(central_current_user_dep),
) -> CentralAiSettingsResponse | None:
    settings_row = session.query(CentralAiSetting).order_by(CentralAiSetting.id.asc()).first()
    if settings_row is None:
        return None
    first_limit = session.query(TenantAiLimit).order_by(TenantAiLimit.id.asc()).first()
    return CentralAiSettingsResponse(
        provider=settings_row.provider,
        model_name=settings_row.config.get("model_name"),
        monthly_request_limit=first_limit.monthly_request_limit if first_limit else 0,
        monthly_token_limit=first_limit.monthly_token_limit if first_limit else 0,
    )


@router.post("/central/ai/generate", response_model=TenantAiGenerateResponse)
def central_ai_generate(
    payload: TenantAiGenerateRequest,
    session: Session = Depends(central_session_dep),
    _: CentralUser = Depends(central_current_user_dep),
) -> TenantAiGenerateResponse:
    from datetime import date

    tenant = session.query(Tenant).filter(Tenant.slug == payload.workspace_slug).one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    ai_settings = session.query(CentralAiSetting).order_by(CentralAiSetting.id.asc()).first()
    if ai_settings is None:
        raise HTTPException(status_code=400, detail="Central AI settings not configured.")

    try:
        decrypted_key = decrypt_value(ai_settings.config.get("api_key", ""))
    except Exception:
        raise HTTPException(status_code=400, detail="Central AI provider key is invalid.")

    if not decrypted_key:
        raise HTTPException(status_code=400, detail="Central AI provider key is invalid.")

    limit = session.query(TenantAiLimit).filter(TenantAiLimit.tenant_id == tenant.id).one_or_none()
    if limit is None:
        limit = TenantAiLimit(tenant_id=tenant.id, monthly_request_limit=0, monthly_token_limit=0)
        session.add(limit)
        session.flush()

    today = date.today()
    monthly_usage = session.query(TenantAiUsageDaily).filter(TenantAiUsageDaily.tenant_id == tenant.id).all()
    month_request_total = sum(
        row.request_count for row in monthly_usage if row.usage_date.year == today.year and row.usage_date.month == today.month
    )
    month_token_total = sum(
        row.token_count for row in monthly_usage if row.usage_date.year == today.year and row.usage_date.month == today.month
    )

    usage = (
        session.query(TenantAiUsageDaily)
        .filter(TenantAiUsageDaily.tenant_id == tenant.id, TenantAiUsageDaily.usage_date == today)
        .one_or_none()
    )
    if usage is None:
        usage = TenantAiUsageDaily(tenant_id=tenant.id, usage_date=today, request_count=0, token_count=0)
        session.add(usage)

    projected_tokens = max(payload.estimated_tokens, len(payload.prompt.split()))
    if limit.monthly_request_limit and month_request_total + 1 > limit.monthly_request_limit:
        raise HTTPException(status_code=429, detail="Monthly AI request limit exceeded.")
    if limit.monthly_token_limit and month_token_total + projected_tokens > limit.monthly_token_limit:
        raise HTTPException(status_code=429, detail="Monthly AI token limit exceeded.")

    generated = (
        f"[{payload.purpose.upper()}] Sugestao automatica para {payload.workspace_slug}: "
        f"{payload.prompt.strip()[:240]}"
    )
    usage.request_count += 1
    usage.token_count += projected_tokens
    session.commit()

    return TenantAiGenerateResponse(
        workspace_slug=payload.workspace_slug,
        purpose=payload.purpose,
        content=generated,
        request_count=usage.request_count,
        token_count=usage.token_count,
    )


@router.get("/central/ai/usage/{workspace_slug}", response_model=TenantAiSummaryResponse)
def get_tenant_ai_usage_summary(
    workspace_slug: str,
    session: Session = Depends(central_session_dep),
    _: CentralUser = Depends(central_current_user_dep),
) -> TenantAiSummaryResponse:
    from datetime import date

    tenant = session.query(Tenant).filter(Tenant.slug == workspace_slug).one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    today = date.today()
    monthly_usage = session.query(TenantAiUsageDaily).filter(TenantAiUsageDaily.tenant_id == tenant.id).all()
    request_total = sum(
        row.request_count for row in monthly_usage if row.usage_date.year == today.year and row.usage_date.month == today.month
    )
    token_total = sum(
        row.token_count for row in monthly_usage if row.usage_date.year == today.year and row.usage_date.month == today.month
    )
    return TenantAiSummaryResponse(
        workspace_slug=workspace_slug,
        request_count=request_total,
        token_count=token_total,
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
        user.email, is_admin=user.is_admin, must_change_password=user.must_change_password, role=user.role
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
        access_token, refresh_token = rotate_tenant_refresh_token(
            session, payload.refresh_token, is_admin=user.is_admin, role=user.role
        )
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


@router.get("/tenant/{workspace_slug}/health", response_model=WorkspaceHealthResponse)
def tenant_workspace_health(
    tenant: Tenant = Depends(tenant_context_dep),
    session: Session = Depends(tenant_session_dep),
) -> WorkspaceHealthResponse:
    schema_versions = [row.version for row in session.query(TenantSchemaVersion).order_by(TenantSchemaVersion.id.asc()).all()]
    whatsapp = session.query(TenantWhatsappAccount).order_by(TenantWhatsappAccount.id.asc()).first()
    return WorkspaceHealthResponse(
        workspace_slug=tenant.slug,
        tenant_status=tenant.status,
        plan_code=tenant.plan_code,
        schema_versions=schema_versions,
        whatsapp_status=whatsapp.status if whatsapp else None,
    )


@router.get("/tenant/{workspace_slug}/users", response_model=list[TenantUserResponse])
def list_tenant_users(
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_admin_user_dep),
) -> list[TenantUserResponse]:
    users = session.query(User).order_by(User.id.asc()).all()
    return [
        TenantUserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_admin=user.is_admin,
            role=user.role,
            permissions=user.permissions or {},
            must_change_password=user.must_change_password,
        )
        for user in users
    ]


@router.get("/tenant/{workspace_slug}/roles", response_model=list[RoleTemplateResponse])
def list_role_templates(
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_admin_user_dep),
) -> list[RoleTemplateResponse]:
    roles = session.query(RoleTemplate).order_by(RoleTemplate.role_name.asc()).all()
    return [RoleTemplateResponse(role_name=role.role_name, permissions=role.permissions or {}) for role in roles]


@router.post("/tenant/{workspace_slug}/roles", response_model=RoleTemplateResponse, status_code=201)
def upsert_role_template(
    payload: RoleTemplateUpsertRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_admin_user_dep),
) -> RoleTemplateResponse:
    role = session.query(RoleTemplate).filter(RoleTemplate.role_name == payload.role_name).one_or_none()
    if role is None:
        role = RoleTemplate(role_name=payload.role_name, permissions=payload.permissions)
        session.add(role)
    else:
        role.permissions = payload.permissions
    session.commit()
    session.refresh(role)
    return RoleTemplateResponse(role_name=role.role_name, permissions=role.permissions or {})


@router.delete("/tenant/{workspace_slug}/roles/{role_name}", status_code=204)
def delete_role_template(
    role_name: str,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_admin_user_dep),
) -> None:
    if role_name == "admin":
        raise HTTPException(status_code=400, detail="Default admin role cannot be removed.")
    role = session.query(RoleTemplate).filter(RoleTemplate.role_name == role_name).one_or_none()
    if role is None:
        raise HTTPException(status_code=404, detail="Role template not found.")
    session.delete(role)
    session.commit()


@router.post("/tenant/{workspace_slug}/users", response_model=TenantUserResponse, status_code=201)
def create_tenant_user(
    payload: TenantUserCreateRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_admin_user_dep),
) -> TenantUserResponse:
    existing = session.query(User).filter(User.email == payload.email).one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="User email already exists.")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        is_admin=payload.is_admin,
        role=payload.role,
        permissions=payload.permissions,
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
        role=user.role,
        permissions=user.permissions or {},
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
    if payload.role is not None:
        user.role = payload.role
    if payload.permissions is not None:
        user.permissions = payload.permissions
    if payload.is_active is not None:
        user.is_active = payload.is_active
    session.commit()
    session.refresh(user)
    return TenantUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin,
        role=user.role,
        permissions=user.permissions or {},
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
    payload: AccountEntryCreateRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_permission_dep("finance.write")),
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
    entry_id: int,
    payload: AccountEntryUpdateRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_permission_dep("finance.write")),
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
def delete_account_receivable(
    entry_id: int, session: Session = Depends(tenant_session_dep), _: User = Depends(tenant_permission_dep("finance.write"))
) -> None:
    entry = session.query(AccountsReceivable).filter(AccountsReceivable.id == entry_id).one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Accounts receivable entry not found.")
    session.delete(entry)
    session.commit()


@router.post("/tenant/{workspace_slug}/finance/accounts-payable", response_model=AccountEntryResponse, status_code=201)
def create_account_payable(
    payload: AccountEntryCreateRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_permission_dep("finance.write")),
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
    entry_id: int,
    payload: AccountEntryUpdateRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_permission_dep("finance.write")),
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
def delete_account_payable(
    entry_id: int, session: Session = Depends(tenant_session_dep), _: User = Depends(tenant_permission_dep("finance.write"))
) -> None:
    entry = session.query(AccountsPayable).filter(AccountsPayable.id == entry_id).one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Accounts payable entry not found.")
    session.delete(entry)
    session.commit()


@router.post("/tenant/{workspace_slug}/sales-orders", response_model=SalesOrderResponse, status_code=201)
def create_sales_order(
    payload: SalesOrderCreateRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_permission_dep("sales.write")),
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
    order_id: int,
    payload: SalesOrderUpdateRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_permission_dep("sales.write")),
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
def delete_sales_order(
    order_id: int, session: Session = Depends(tenant_session_dep), _: User = Depends(tenant_permission_dep("sales.write"))
) -> None:
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
    _: User = Depends(tenant_permission_dep("sales.write")),
) -> ProposalResponse:
    if payload.client_id is not None:
        client = session.query(Client).filter(Client.id == payload.client_id).one_or_none()
        if client is None:
            raise HTTPException(status_code=404, detail="Client not found.")
    if payload.sales_order_id is not None:
        order = session.query(SalesOrder).filter(SalesOrder.id == payload.sales_order_id).one_or_none()
        if order is None:
            raise HTTPException(status_code=404, detail="Sales order not found.")
    proposal = Proposal(
        client_id=payload.client_id,
        sales_order_id=payload.sales_order_id,
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
        sales_order_id=proposal.sales_order_id,
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
            sales_order_id=proposal.sales_order_id,
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
    _: User = Depends(tenant_permission_dep("sales.write")),
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
        sales_order_id=proposal.sales_order_id,
        title=proposal.title,
        template_name=proposal.template_name,
        pdf_path=proposal.pdf_path,
        is_sendable=proposal.is_sendable,
    )


@router.delete("/tenant/{workspace_slug}/proposals/{proposal_id}", status_code=204)
def delete_proposal(
    proposal_id: int, session: Session = Depends(tenant_session_dep), _: User = Depends(tenant_permission_dep("sales.write"))
) -> None:
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
    _: User = Depends(tenant_permission_dep("contracts.write")),
) -> ContractResponse:
    if payload.client_id is not None:
        client = session.query(Client).filter(Client.id == payload.client_id).one_or_none()
        if client is None:
            raise HTTPException(status_code=404, detail="Client not found.")
    if payload.sales_order_id is not None:
        order = session.query(SalesOrder).filter(SalesOrder.id == payload.sales_order_id).one_or_none()
        if order is None:
            raise HTTPException(status_code=404, detail="Sales order not found.")
    contract = Contract(
        client_id=payload.client_id,
        sales_order_id=payload.sales_order_id,
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
        sales_order_id=contract.sales_order_id,
        title=contract.title,
        template_name=contract.template_name,
        pdf_path=contract.pdf_path,
        status=contract.status,
        signed_file_path=contract.signed_file_path,
    )


@router.get("/tenant/{workspace_slug}/contracts", response_model=list[ContractResponse])
def list_contracts(session: Session = Depends(tenant_session_dep)) -> list[ContractResponse]:
    contracts = session.query(Contract).order_by(Contract.id.desc()).all()
    return [
        ContractResponse(
            id=contract.id,
            client_id=contract.client_id,
            sales_order_id=contract.sales_order_id,
            title=contract.title,
            template_name=contract.template_name,
            pdf_path=contract.pdf_path,
            status=contract.status,
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
    _: User = Depends(tenant_permission_dep("contracts.write")),
) -> ContractResponse:
    contract = session.query(Contract).filter(Contract.id == contract_id).one_or_none()
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found.")
    if payload.title is not None:
        contract.title = payload.title
    if payload.template_name is not None:
        contract.template_name = payload.template_name
    if payload.status is not None:
        if payload.status not in {"draft", "sent", "signed", "cancelled"}:
            raise HTTPException(status_code=422, detail="Invalid contract status.")
        contract.status = payload.status
    contract.pdf_path = _write_document_file(workspace_slug, "contracts", contract.id, contract.title)
    session.commit()
    session.refresh(contract)
    return ContractResponse(
        id=contract.id,
        client_id=contract.client_id,
        sales_order_id=contract.sales_order_id,
        title=contract.title,
        template_name=contract.template_name,
        pdf_path=contract.pdf_path,
        status=contract.status,
        signed_file_path=contract.signed_file_path,
    )


@router.post("/tenant/{workspace_slug}/contracts/{contract_id}/signed-file", response_model=ContractResponse)
def upload_signed_contract_file(
    workspace_slug: str,
    contract_id: int,
    payload: ContractSignedFileRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_permission_dep("contracts.write")),
) -> ContractResponse:
    contract = session.query(Contract).filter(Contract.id == contract_id).one_or_none()
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found.")
    contract.signed_file_path = _write_signed_contract_file(workspace_slug, contract.id, payload.file_name, payload.content)
    contract.status = "signed"
    session.commit()
    session.refresh(contract)
    return ContractResponse(
        id=contract.id,
        client_id=contract.client_id,
        sales_order_id=contract.sales_order_id,
        title=contract.title,
        template_name=contract.template_name,
        pdf_path=contract.pdf_path,
        status=contract.status,
        signed_file_path=contract.signed_file_path,
    )


@router.delete("/tenant/{workspace_slug}/contracts/{contract_id}", status_code=204)
def delete_contract(
    contract_id: int, session: Session = Depends(tenant_session_dep), _: User = Depends(tenant_permission_dep("contracts.write"))
) -> None:
    contract = session.query(Contract).filter(Contract.id == contract_id).one_or_none()
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found.")
    session.delete(contract)
    session.commit()


@router.post("/tenant/{workspace_slug}/whatsapp/session", response_model=WhatsappSessionResponse, status_code=201)
def upsert_whatsapp_session(
    payload: WhatsappSessionRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_permission_dep("whatsapp.manage")),
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


@router.post("/tenant/{workspace_slug}/whatsapp/outbound", status_code=201)
def whatsapp_outbound(
    payload: WhatsappOutboundRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_permission_dep("whatsapp.send")),
) -> dict[str, str | int]:
    if payload.client_id is None and payload.lead_id is None:
        raise HTTPException(status_code=422, detail="client_id or lead_id is required.")
    if payload.client_id is not None:
        client = session.query(Client).filter(Client.id == payload.client_id).one_or_none()
        if client is None:
            raise HTTPException(status_code=404, detail="Client not found.")
    if payload.lead_id is not None:
        lead = session.query(Lead).filter(Lead.id == payload.lead_id).one_or_none()
        if lead is None:
            raise HTTPException(status_code=404, detail="Lead not found.")

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
    return {"status": message.status, "message_id": message.id}


@router.post("/tenant/{workspace_slug}/whatsapp/status", status_code=200)
def whatsapp_status(
    payload: WhatsappStatusRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_permission_dep("whatsapp.manage")),
) -> dict[str, str]:
    if payload.status not in {"sending", "sent", "delivered", "read", "failed"}:
        raise HTTPException(status_code=422, detail="Invalid message status.")
    message = session.query(Message).filter(Message.id == payload.message_id).one_or_none()
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found.")
    message.status = payload.status
    session.commit()
    return {"status": message.status}


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


@router.post("/tenant/{workspace_slug}/storage/files", response_model=StorageFileResponse, status_code=201)
def upload_workspace_file(
    workspace_slug: str,
    payload: StorageFileRequest,
    session: Session = Depends(tenant_session_dep),
) -> StorageFileResponse:
    _ = session
    file_path = save_workspace_file(workspace_slug, payload.bucket, payload.file_name, payload.content)
    signed_url, expires_at = generate_signed_url(file_path)
    return StorageFileResponse(
        file_path=file_path,
        signed_url=signed_url,
        expires_at=expires_at.isoformat(),
    )


@router.get("/storage/signed", response_model=StorageFileResponse)
def resolve_signed_storage(path: str, token: str):
    from datetime import UTC, datetime
    from pathlib import Path
    from urllib.parse import unquote

    decoded_path = unquote(path)
    decoded_token = unquote(token)
    try:
        token_file, token_expiry = decoded_token.split(":")
        expiry_ts = int(token_expiry)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid signed token.")

    if Path(decoded_path).name != token_file:
        raise HTTPException(status_code=403, detail="Signed token does not match file.")
    if datetime.now(UTC).timestamp() > expiry_ts:
        raise HTTPException(status_code=403, detail="Signed token expired.")
    file = Path(decoded_path)
    if not file.exists():
        raise HTTPException(status_code=404, detail="File not found.")

    media_type = "application/octet-stream"
    suffix = file.suffix.lower()
    if suffix in {".txt", ".csv", ".log"}:
        media_type = "text/plain; charset=utf-8"
    elif suffix == ".pdf":
        media_type = "application/pdf"
    return FileResponse(path=file, filename=file.name, media_type=media_type)


@router.post("/tenant/{workspace_slug}/finance/categories", response_model=FinanceCategoryResponse, status_code=201)
def create_finance_category(
    payload: FinanceCategoryCreateRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_permission_dep("finance.write")),
) -> FinanceCategoryResponse:
    category = FinanceCategory(name=payload.name, entry_type=payload.entry_type)
    session.add(category)
    session.commit()
    session.refresh(category)
    return FinanceCategoryResponse(id=category.id, name=category.name, entry_type=category.entry_type)


@router.get("/tenant/{workspace_slug}/finance/categories", response_model=list[FinanceCategoryResponse])
def list_finance_categories(
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_permission_dep("finance.write")),
) -> list[FinanceCategoryResponse]:
    items = session.query(FinanceCategory).order_by(FinanceCategory.name.asc()).all()
    return [FinanceCategoryResponse(id=item.id, name=item.name, entry_type=item.entry_type) for item in items]


@router.post("/tenant/{workspace_slug}/finance/cost-centers", response_model=CostCenterResponse, status_code=201)
def create_cost_center(
    payload: CostCenterCreateRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_permission_dep("finance.write")),
) -> CostCenterResponse:
    center = CostCenter(name=payload.name)
    session.add(center)
    session.commit()
    session.refresh(center)
    return CostCenterResponse(id=center.id, name=center.name)


@router.get("/tenant/{workspace_slug}/finance/cost-centers", response_model=list[CostCenterResponse])
def list_cost_centers(
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_permission_dep("finance.write")),
) -> list[CostCenterResponse]:
    items = session.query(CostCenter).order_by(CostCenter.name.asc()).all()
    return [CostCenterResponse(id=item.id, name=item.name) for item in items]


@router.get("/tenant/{workspace_slug}/finance/export", response_model=FinanceExportResponse)
def export_finance(
    export_format: str = "csv",
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_permission_dep("finance.write")),
) -> FinanceExportResponse:
    receivables = session.query(AccountsReceivable).order_by(AccountsReceivable.id.asc()).all()
    payables = session.query(AccountsPayable).order_by(AccountsPayable.id.asc()).all()
    if export_format not in {"csv", "txt"}:
        raise HTTPException(status_code=422, detail="Invalid export format.")

    lines = ["type,id,due_date,amount,status,category,cost_center"]
    for row in receivables:
        lines.append(
            f"receivable,{row.id},{row.due_date.isoformat()},{float(row.amount)},{row.status},{row.category or ''},{row.cost_center or ''}"
        )
    for row in payables:
        lines.append(
            f"payable,{row.id},{row.due_date.isoformat()},{float(row.amount)},{row.status},{row.category or ''},{row.cost_center or ''}"
        )
    return FinanceExportResponse(format=export_format, content="\n".join(lines))


@router.get("/tenant/{workspace_slug}/finance/dashboard", response_model=FinanceDashboardResponse)
def finance_dashboard(
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_permission_dep("finance.write")),
) -> FinanceDashboardResponse:
    receivables = session.query(AccountsReceivable).all()
    payables = session.query(AccountsPayable).all()
    receivable_total = sum(float(row.amount) for row in receivables)
    payable_total = sum(float(row.amount) for row in payables)
    receivable_pending = sum(float(row.amount) for row in receivables if row.status == "pending")
    payable_pending = sum(float(row.amount) for row in payables if row.status == "pending")
    return FinanceDashboardResponse(
        receivable_total=receivable_total,
        payable_total=payable_total,
        receivable_pending=receivable_pending,
        payable_pending=payable_pending,
        receivable_count=len(receivables),
        payable_count=len(payables),
    )


@router.get("/tenant/{workspace_slug}/dashboard/commercial", response_model=CommercialDashboardResponse)
def commercial_dashboard(
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_permission_dep("sales.write")),
) -> CommercialDashboardResponse:
    leads = session.query(Lead).all()
    clients = session.query(Client).all()
    orders = session.query(SalesOrder).all()
    messages = session.query(Message).all()
    return CommercialDashboardResponse(
        lead_count=len(leads),
        client_count=len(clients),
        converted_lead_count=sum(1 for lead in leads if lead.conversion_date is not None),
        sales_order_count=len(orders),
        sales_total=sum(float(order.total_amount) for order in orders),
        inbound_message_count=sum(1 for message in messages if message.direction == "inbound"),
        outbound_message_count=sum(1 for message in messages if message.direction == "outbound"),
    )


@router.post("/tenant/{workspace_slug}/ai/usage", status_code=201)
def register_tenant_ai_usage(
    workspace_slug: str,
    request_count: int,
    token_count: int,
    session: Session = Depends(central_session_dep),
    _: CentralUser = Depends(central_current_user_dep),
) -> dict[str, int | str]:
    from datetime import date

    tenant = session.query(Tenant).filter(Tenant.slug == workspace_slug).one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    usage = (
        session.query(TenantAiUsageDaily)
        .filter(TenantAiUsageDaily.tenant_id == tenant.id, TenantAiUsageDaily.usage_date == date.today())
        .one_or_none()
    )
    if usage is None:
        usage = TenantAiUsageDaily(
            tenant_id=tenant.id,
            usage_date=date.today(),
            request_count=0,
            token_count=0,
        )
        session.add(usage)

    usage.request_count += request_count
    usage.token_count += token_count
    session.commit()
    return {
        "workspace": workspace_slug,
        "request_count": usage.request_count,
        "token_count": usage.token_count,
    }


@router.post("/central/analytics/run-daily", status_code=201)
def run_daily_analytics(
    session: Session = Depends(central_session_dep),
    _: CentralUser = Depends(central_current_user_dep),
) -> dict[str, int]:
    from datetime import date

    processed = 0
    created_tasks = 0

    tenants = session.query(Tenant).all()
    for tenant in tenants:
        processed += 1
        usage_rows = session.query(TenantAiUsageDaily).filter(TenantAiUsageDaily.tenant_id == tenant.id).all()
        request_total = sum(row.request_count for row in usage_rows)
        score = max(0, 100 - request_total)
        status = "healthy"
        if score < 70:
            status = "warning"
        if score < 40:
            status = "risk"

        health_row = session.query(TenantHealthScore).filter(TenantHealthScore.tenant_id == tenant.id).one_or_none()
        if health_row is None:
            health_row = TenantHealthScore(tenant_id=tenant.id, score=score, status=status)
            session.add(health_row)
        else:
            health_row.score = score
            health_row.status = status

        session.add(
            TenantAnalyticsSnapshot(
                tenant_id=tenant.id,
                snapshot_date=date.today(),
                period_type="daily",
                metrics={
                    "ai_requests": request_total,
                    "health_score": score,
                    "health_status": status,
                },
            )
        )

        existing_task = (
            session.query(CentralTask)
            .filter(CentralTask.tenant_id == tenant.id, CentralTask.status == "open", CentralTask.title == "Tenant health risk")
            .one_or_none()
        )
        if status == "risk" and existing_task is None:
            session.add(
                CentralTask(
                    tenant_id=tenant.id,
                    title="Tenant health risk",
                    description=f"Workspace {tenant.slug} entered risk status during daily analytics.",
                    status="open",
                )
            )
            created_tasks += 1

    session.commit()
    return {"processed_tenants": processed, "created_tasks": created_tasks}


@router.post("/central/analytics/run-monthly", status_code=201)
def run_monthly_analytics(
    session: Session = Depends(central_session_dep),
    _: CentralUser = Depends(central_current_user_dep),
) -> dict[str, int]:
    from datetime import date

    processed = 0
    today = date.today()
    tenants = session.query(Tenant).all()
    for tenant in tenants:
        processed += 1
        usage_rows = session.query(TenantAiUsageDaily).filter(TenantAiUsageDaily.tenant_id == tenant.id).all()
        metrics = {
            "ai_requests": sum(
                row.request_count for row in usage_rows if row.usage_date.year == today.year and row.usage_date.month == today.month
            ),
            "ai_tokens": sum(
                row.token_count for row in usage_rows if row.usage_date.year == today.year and row.usage_date.month == today.month
            ),
        }
        session.add(
            TenantAnalyticsSnapshot(
                tenant_id=tenant.id,
                snapshot_date=today,
                period_type="monthly",
                metrics=metrics,
            )
        )
    session.commit()
    return {"processed_tenants": processed}


@router.get("/central/analytics/{workspace_slug}/latest", response_model=TenantAnalyticsSnapshotResponse)
def get_latest_analytics_snapshot(
    workspace_slug: str,
    period_type: str = "daily",
    session: Session = Depends(central_session_dep),
    _: CentralUser = Depends(central_current_user_dep),
) -> TenantAnalyticsSnapshotResponse:
    tenant = session.query(Tenant).filter(Tenant.slug == workspace_slug).one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found.")
    snapshot = (
        session.query(TenantAnalyticsSnapshot)
        .filter(TenantAnalyticsSnapshot.tenant_id == tenant.id, TenantAnalyticsSnapshot.period_type == period_type)
        .order_by(TenantAnalyticsSnapshot.snapshot_date.desc(), TenantAnalyticsSnapshot.id.desc())
        .first()
    )
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Analytics snapshot not found.")
    return TenantAnalyticsSnapshotResponse(
        workspace_slug=workspace_slug,
        period_type=snapshot.period_type,
        snapshot_date=snapshot.snapshot_date.isoformat(),
        metrics=snapshot.metrics,
    )


@router.post("/tenant/{workspace_slug}/lead-radar/runs", response_model=LeadRadarRunResponse, status_code=201)
def create_lead_radar_run(
    workspace_slug: str,
    payload: LeadRadarRunCreateRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_permission_dep("leadradar.run")),
) -> LeadRadarRunResponse:
    summary = {
        "workspace": workspace_slug,
        "query": payload.query,
        "captured": 0,
        "deduped": 0,
    }
    run = LeadRadarRun(status="queued", source=payload.source, summary=summary)
    session.add(run)
    session.commit()
    session.refresh(run)
    return LeadRadarRunResponse(id=run.id, status=run.status, source=run.source, summary=run.summary)


@router.post("/tenant/{workspace_slug}/lead-radar/runs/{run_id}/process", response_model=LeadRadarRunResponse)
def process_lead_radar_run(
    run_id: int,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_permission_dep("leadradar.run")),
) -> LeadRadarRunResponse:
    run = session.query(LeadRadarRun).filter(LeadRadarRun.id == run_id).one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Lead radar run not found.")
    query_text = str(run.summary.get("query", "LeadRadar")).strip()
    generated_names = [f"{query_text} Prospect {index}" for index in range(1, 6)]
    created = 0
    deduped = 0
    for index, name in enumerate(generated_names, start=1):
        synthetic_phone = f"lradar-{run.id}-{index}"
        existing_client = session.query(Client).filter(Client.phone == synthetic_phone).one_or_none()
        existing_lead = session.query(Lead).filter(Lead.phone == synthetic_phone).one_or_none()
        if existing_client is not None or existing_lead is not None:
            deduped += 1
            continue
        session.add(
            Lead(
                name=name,
                phone=synthetic_phone,
                source=run.source,
                manual_classification="new",
            )
        )
        created += 1
    updated_summary = dict(run.summary)
    updated_summary["captured"] = updated_summary.get("captured", 0) + created
    updated_summary["deduped"] = updated_summary.get("deduped", 0) + deduped
    run.summary = updated_summary
    run.status = "processed"
    session.commit()
    session.refresh(run)
    return LeadRadarRunResponse(id=run.id, status=run.status, source=run.source, summary=run.summary)


@router.post("/tenant/{workspace_slug}/lead-radar/callback", response_model=LeadRadarRunResponse, status_code=201)
def lead_radar_callback(
    workspace_slug: str,
    payload: LeadRadarCallbackRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_permission_dep("leadradar.run")),
) -> LeadRadarRunResponse:
    if payload.external_run_id:
        existing_run = (
            session.query(LeadRadarRun).filter(LeadRadarRun.external_run_id == payload.external_run_id).one_or_none()
        )
        if existing_run is not None:
            return LeadRadarRunResponse(
                id=existing_run.id,
                status=existing_run.status,
                source=existing_run.source,
                summary=existing_run.summary,
            )

    created = 0
    deduped = 0
    for item in payload.items:
        existing_client = None
        existing_lead = None

        if item.phone:
            existing_client = session.query(Client).filter(Client.phone == item.phone).one_or_none()
            existing_lead = session.query(Lead).filter(Lead.phone == item.phone).one_or_none()
        if existing_client is None and existing_lead is None and item.email:
            existing_client = session.query(Client).filter(Client.email == item.email).one_or_none()
            existing_lead = session.query(Lead).filter(Lead.email == item.email).one_or_none()

        if existing_client is not None or existing_lead is not None:
            deduped += 1
            continue

        session.add(
            Lead(
                name=item.name,
                phone=item.phone,
                email=item.email,
                source=payload.source,
                manual_classification="radar",
                metadata_json={"cnpj": item.cnpj, "workspace": workspace_slug},
            )
        )
        created += 1

    run = LeadRadarRun(
        external_run_id=payload.external_run_id,
        status="processed",
        source=payload.source,
        summary={
            "workspace": workspace_slug,
            "query": payload.query,
            "captured": created,
            "deduped": deduped,
            "mode": "callback",
        },
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return LeadRadarRunResponse(id=run.id, status=run.status, source=run.source, summary=run.summary)


@router.get("/tenant/{workspace_slug}/lead-radar/runs", response_model=list[LeadRadarRunResponse])
def list_lead_radar_runs(
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_permission_dep("marketplace.write")),
) -> list[LeadRadarRunResponse]:
    runs = session.query(LeadRadarRun).order_by(LeadRadarRun.id.desc()).all()
    return [LeadRadarRunResponse(id=run.id, status=run.status, source=run.source, summary=run.summary) for run in runs]


@router.post("/tenant/{workspace_slug}/marketplace/webhook", response_model=SalesOrderResponse, status_code=201)
def marketplace_webhook(
    payload: MarketplaceWebhookRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(tenant_permission_dep("marketplace.write")),
) -> SalesOrderResponse:
    from datetime import date

    existing_event = (
        session.query(MarketplaceEvent).filter(MarketplaceEvent.external_order_id == payload.external_order_id).one_or_none()
    )
    if existing_event is not None and existing_event.sales_order_id is not None:
        existing_order = session.query(SalesOrder).filter(SalesOrder.id == existing_event.sales_order_id).one_or_none()
        if existing_order is not None:
            return SalesOrderResponse(
                id=existing_order.id,
                client_id=existing_order.client_id,
                order_type=existing_order.order_type,
                duration_months=existing_order.duration_months,
                total_amount=float(existing_order.total_amount),
                status=existing_order.status,
            )

    client = None
    if payload.client_email:
        client = session.query(Client).filter(Client.email == payload.client_email).one_or_none()
    if client is None and payload.client_phone:
        client = session.query(Client).filter(Client.phone == payload.client_phone).one_or_none()
    if client is None:
        client = Client(
            name=payload.client_name,
            email=payload.client_email,
            phone=payload.client_phone,
        )
        session.add(client)
        session.flush()

    order = SalesOrder(
        client_id=client.id,
        order_type="one_time",
        duration_months=None,
        total_amount=payload.total_amount,
        status="confirmed",
    )
    session.add(order)
    session.flush()

    session.add(
        SalesItem(
            sales_order_id=order.id,
            description=f"Marketplace {payload.channel} order {payload.external_order_id}",
            quantity=1,
            unit_price=payload.total_amount,
        )
    )
    session.add(
        AccountsReceivable(
            sales_order_id=order.id,
            due_date=date.fromisoformat(payload.first_due_date),
            amount=payload.total_amount,
            status="pending",
            category="marketplace",
            cost_center=payload.channel,
        )
    )
    session.add(
        MarketplaceEvent(
            channel=payload.channel,
            external_order_id=payload.external_order_id,
            sales_order_id=order.id,
            payload={
                "client_name": payload.client_name,
                "client_email": payload.client_email,
                "client_phone": payload.client_phone,
                "total_amount": payload.total_amount,
            },
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
