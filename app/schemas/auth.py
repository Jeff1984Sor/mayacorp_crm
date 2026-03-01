from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class CentralUserResponse(BaseModel):
    email: EmailStr
    full_name: str
    must_change_password: bool


class CentralPasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class CentralDashboardResponse(BaseModel):
    tenant_count: int
    active_tenant_count: int
    open_task_count: int
    pending_invoice_count: int
    total_invoice_amount: float


class RefreshRequest(BaseModel):
    refresh_token: str


class TenantLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TenantRefreshRequest(BaseModel):
    refresh_token: str


class CentralAiSettingsRequest(BaseModel):
    provider: str
    api_key: str
    model_name: str | None = None
    monthly_request_limit: int = 0
    monthly_token_limit: int = 0


class CentralAiSettingsResponse(BaseModel):
    provider: str
    model_name: str | None
    monthly_request_limit: int
    monthly_token_limit: int


class TenantAiGenerateRequest(BaseModel):
    workspace_slug: str
    purpose: str
    prompt: str
    estimated_tokens: int = 0


class TenantAiGenerateResponse(BaseModel):
    workspace_slug: str
    purpose: str
    content: str
    request_count: int
    token_count: int


class TenantAiSummaryResponse(BaseModel):
    workspace_slug: str
    request_count: int
    token_count: int


class TenantAnalyticsSnapshotResponse(BaseModel):
    workspace_slug: str
    period_type: str
    snapshot_date: str
    metrics: dict
