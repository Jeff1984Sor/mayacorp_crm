from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class TenantUserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=4, max_length=128)
    is_admin: bool = False


class TenantUserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_admin: bool
    must_change_password: bool


class TenantUserUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    is_admin: bool | None = None
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


class ProposalCreateRequest(BaseModel):
    client_id: int | None = None
    title: str = Field(min_length=2, max_length=255)
    template_name: str | None = Field(default=None, max_length=120)
    is_sendable: bool = True


class ProposalResponse(BaseModel):
    id: int
    client_id: int | None
    title: str
    template_name: str | None
    pdf_path: str | None
    is_sendable: bool


class ContractCreateRequest(BaseModel):
    client_id: int | None = None
    title: str = Field(min_length=2, max_length=255)
    template_name: str | None = Field(default=None, max_length=120)


class ContractResponse(BaseModel):
    id: int
    client_id: int | None
    title: str
    template_name: str | None
    pdf_path: str | None
    signed_file_path: str | None
