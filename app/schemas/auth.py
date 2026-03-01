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
