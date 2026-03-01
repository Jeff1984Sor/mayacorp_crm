from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class TenantUserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=4, max_length=128)
    is_admin: bool = False
    role: str = Field(default="staff", max_length=40)
    permissions: dict = Field(default_factory=dict)


class TenantUserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_admin: bool
    role: str
    permissions: dict
    must_change_password: bool


class TenantUserUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    is_admin: bool | None = None
    role: str | None = Field(default=None, max_length=40)
    permissions: dict | None = None
    is_active: bool | None = None


class LeadCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    source: str | None = Field(default=None, max_length=80)
    manual_classification: str | None = Field(default=None, max_length=80)


class LeadResponse(BaseModel):
    id: int
    name: str
    email: EmailStr | None
    phone: str | None
    source: str | None
    manual_classification: str | None
    conversion_date: datetime | None


class LeadUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    source: str | None = Field(default=None, max_length=80)
    manual_classification: str | None = Field(default=None, max_length=80)


class ClientCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    source_lead_id: int | None = None


class ClientResponse(BaseModel):
    id: int
    name: str
    email: EmailStr | None
    phone: str | None
    source_lead_id: int | None


class ClientUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)


class LeadConversionRequest(BaseModel):
    client_name: str | None = Field(default=None, min_length=2, max_length=255)
    client_email: EmailStr | None = None
    client_phone: str | None = Field(default=None, max_length=40)


class AccountEntryCreateRequest(BaseModel):
    amount: float = Field(gt=0)
    due_date: str
    category: str | None = Field(default=None, max_length=80)
    cost_center: str | None = Field(default=None, max_length=80)


class AccountEntryResponse(BaseModel):
    id: int
    amount: float
    due_date: str
    status: str
    category: str | None
    cost_center: str | None


class AccountEntryUpdateRequest(BaseModel):
    amount: float | None = Field(default=None, gt=0)
    due_date: str | None = None
    status: str | None = Field(default=None, max_length=40)
    category: str | None = Field(default=None, max_length=80)
    cost_center: str | None = Field(default=None, max_length=80)


class SalesItemCreateRequest(BaseModel):
    description: str = Field(min_length=2, max_length=255)
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)


class SalesItemResponse(BaseModel):
    id: int
    description: str
    quantity: float
    unit_price: float


class SalesOrderCreateRequest(BaseModel):
    client_id: int | None = None
    order_type: str = Field(default="one_time", max_length=20)
    duration_months: int | None = Field(default=None, ge=1, le=24)
    installments: int = Field(default=1, ge=1, le=24)
    first_due_date: str
    category: str | None = Field(default=None, max_length=80)
    cost_center: str | None = Field(default=None, max_length=80)
    items: list[SalesItemCreateRequest] = Field(min_length=1)


class SalesOrderResponse(BaseModel):
    id: int
    client_id: int | None
    order_type: str
    duration_months: int | None
    total_amount: float
    status: str


class SalesOrderUpdateRequest(BaseModel):
    status: str | None = Field(default=None, max_length=40)
    order_type: str | None = Field(default=None, max_length=20)
    duration_months: int | None = Field(default=None, ge=1, le=24)


class ProposalCreateRequest(BaseModel):
    client_id: int | None = None
    sales_order_id: int | None = None
    title: str = Field(min_length=2, max_length=255)
    template_name: str | None = Field(default=None, max_length=120)
    is_sendable: bool = True


class ProposalResponse(BaseModel):
    id: int
    client_id: int | None
    sales_order_id: int | None
    title: str
    template_name: str | None
    pdf_path: str | None
    is_sendable: bool


class ProposalUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    template_name: str | None = Field(default=None, max_length=120)
    is_sendable: bool | None = None


class ContractCreateRequest(BaseModel):
    client_id: int | None = None
    sales_order_id: int | None = None
    title: str = Field(min_length=2, max_length=255)
    template_name: str | None = Field(default=None, max_length=120)


class ContractResponse(BaseModel):
    id: int
    client_id: int | None
    sales_order_id: int | None
    title: str
    template_name: str | None
    pdf_path: str | None
    status: str
    signed_file_path: str | None


class ContractUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    template_name: str | None = Field(default=None, max_length=120)
    status: str | None = Field(default=None, max_length=40)


class WhatsappSessionRequest(BaseModel):
    provider_session_id: str | None = Field(default=None, max_length=120)


class WhatsappSessionResponse(BaseModel):
    id: int
    provider_session_id: str | None
    status: str
    last_qr_code: str | None


class WhatsappInboundRequest(BaseModel):
    external_sender: str = Field(min_length=3, max_length=120)
    body: str = Field(min_length=1)
    lead_id: int | None = None
    client_id: int | None = None


class WhatsappUnmatchedResponse(BaseModel):
    id: int
    external_sender: str
    body: str
    matched: bool


class WhatsappOutboundRequest(BaseModel):
    body: str = Field(min_length=1)
    lead_id: int | None = None
    client_id: int | None = None


class WhatsappStatusRequest(BaseModel):
    message_id: int
    status: str = Field(min_length=3, max_length=20)


class LeadRadarRunCreateRequest(BaseModel):
    source: str = Field(default="google_places", max_length=80)
    query: str = Field(min_length=2, max_length=255)


class LeadRadarRunResponse(BaseModel):
    id: int
    status: str
    source: str
    summary: dict


class LeadRadarCallbackItem(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None
    cnpj: str | None = Field(default=None, max_length=40)


class LeadRadarCallbackRequest(BaseModel):
    source: str = Field(default="google_places", max_length=80)
    query: str = Field(min_length=2, max_length=255)
    external_run_id: str | None = Field(default=None, max_length=120)
    items: list[LeadRadarCallbackItem] = Field(min_length=1)


class MarketplaceWebhookRequest(BaseModel):
    channel: str = Field(min_length=2, max_length=80)
    external_order_id: str = Field(min_length=2, max_length=120)
    client_name: str = Field(min_length=2, max_length=255)
    client_email: EmailStr | None = None
    client_phone: str | None = Field(default=None, max_length=40)
    total_amount: float = Field(gt=0)
    first_due_date: str


class ContractSignedFileRequest(BaseModel):
    file_name: str = Field(min_length=3, max_length=255)
    content: str = Field(min_length=1)


class WorkspaceHealthResponse(BaseModel):
    workspace_slug: str
    tenant_status: str
    plan_code: str
    schema_versions: list[str]
    whatsapp_status: str | None


class StorageFileRequest(BaseModel):
    bucket: str = Field(min_length=2, max_length=80)
    file_name: str = Field(min_length=2, max_length=255)
    content: str = Field(min_length=1)


class StorageFileResponse(BaseModel):
    file_path: str
    signed_url: str
    expires_at: str


class FinanceCategoryCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    entry_type: str = Field(default="both", max_length=20)


class FinanceCategoryResponse(BaseModel):
    id: int
    name: str
    entry_type: str


class CostCenterCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class CostCenterResponse(BaseModel):
    id: int
    name: str


class FinanceExportResponse(BaseModel):
    format: str
    content: str


class StorageResolvedResponse(BaseModel):
    file_path: str
    file_name: str
    content: str
    expires_at: str


class FinanceDashboardResponse(BaseModel):
    receivable_total: float
    payable_total: float
    receivable_pending: float
    payable_pending: float
    receivable_count: int
    payable_count: int


class CommercialDashboardResponse(BaseModel):
    lead_count: int
    client_count: int
    converted_lead_count: int
    sales_order_count: int
    sales_total: float
    inbound_message_count: int
    outbound_message_count: int


class RoleTemplateResponse(BaseModel):
    role_name: str
    permissions: dict


class RoleTemplateUpsertRequest(BaseModel):
    role_name: str = Field(min_length=2, max_length=40)
    permissions: dict = Field(default_factory=dict)
