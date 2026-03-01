from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_tenant_session
from app.models.central import CentralUser
from app.db.session import get_central_session
from app.models.central import Tenant
from app.models.tenant import User

bearer_scheme = HTTPBearer(auto_error=False)


def central_session_dep(session: Session = Depends(get_central_session)) -> Session:
    return session


def tenant_context_dep(
    request: Request,
    workspace_slug: str | None = Header(default=None, alias="X-Workspace-Slug"),
    session: Session = Depends(get_central_session),
) -> Tenant:
    slug = workspace_slug or request.path_params.get("workspace_slug")
    if not slug:
        raise HTTPException(status_code=400, detail="Workspace slug is required.")

    tenant = session.query(Tenant).filter(Tenant.slug == slug).one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    request.state.tenant = tenant
    return tenant


def central_current_user_dep(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_central_session),
) -> CentralUser:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization token is required.")
    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token.")

    if payload.get("scope") != "central":
        raise HTTPException(status_code=403, detail="Invalid token scope.")

    email = payload.get("sub")
    user = session.query(CentralUser).filter(CentralUser.email == email).one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found.")
    return user


def tenant_session_dep(tenant: Tenant = Depends(tenant_context_dep)):
    yield from get_tenant_session(tenant.database_url)


def tenant_current_user_dep(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(tenant_session_dep),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization token is required.")
    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token.")

    if payload.get("scope") != "tenant" or payload.get("type") != "access":
        raise HTTPException(status_code=403, detail="Invalid token scope.")

    email = payload.get("sub")
    user = session.query(User).filter(User.email == email).one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found.")
    return user


def tenant_admin_user_dep(current_user: User = Depends(tenant_current_user_dep)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin permission required.")
    return current_user
