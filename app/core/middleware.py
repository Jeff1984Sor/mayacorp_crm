from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class TenantResolutionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.tenant = None
        workspace_slug = request.headers.get("X-Workspace-Slug")
        if workspace_slug:
            request.state.workspace_slug = workspace_slug
        return await call_next(request)
