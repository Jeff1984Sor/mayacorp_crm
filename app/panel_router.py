from __future__ import annotations

from fastapi import APIRouter

from app.panel_auth_router import panel_auth_router
from app.panel_crm_router import panel_crm_router
from app.panel_finance_router import panel_finance_router
from app.panel_summary_router import panel_summary_router
from app.panel_whatsapp_router import panel_whatsapp_router

panel_router = APIRouter(tags=["health"])
panel_router.include_router(panel_auth_router)
panel_router.include_router(panel_crm_router)
panel_router.include_router(panel_finance_router)
panel_router.include_router(panel_summary_router)
panel_router.include_router(panel_whatsapp_router)
