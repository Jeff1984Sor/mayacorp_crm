from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_central_session
from app.models.central import Tenant


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
