from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class TenantCreateRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=255)
    workspace_slug: str = Field(min_length=2, max_length=80)
    company_document: str | None = Field(default=None, max_length=40)
    admin_name: str = Field(min_length=2, max_length=255)
    admin_email: EmailStr
    admin_password: str = Field(min_length=4, max_length=128)
    plan_code: str = Field(min_length=2, max_length=80)
    addon_codes: list[str] = Field(default_factory=list)
    billing_day: int = Field(default=1, ge=1, le=28)
    discount_percent: float = Field(default=0, ge=0, le=100)
    generate_invoice: bool = False
    issue_fiscal_document: bool = False


class TenantCreateResponse(BaseModel):
    tenant_id: int
    tenant_db_url: str
    message: str
