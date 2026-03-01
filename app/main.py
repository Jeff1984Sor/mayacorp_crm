from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import router
from app.core.middleware import TenantResolutionMiddleware
from app.services.bootstrap import bootstrap_central_database


bootstrap_central_database()

app = FastAPI(title="Mayacorp CRM", version="0.1.0")
app.add_middleware(TenantResolutionMiddleware)
app.include_router(router)
