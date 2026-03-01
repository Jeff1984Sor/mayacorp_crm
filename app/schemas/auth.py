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
