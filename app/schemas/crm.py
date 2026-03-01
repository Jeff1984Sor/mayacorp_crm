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
