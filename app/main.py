from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.middleware import TenantResolutionMiddleware
from app.panel_router import panel_router
from app.services.bootstrap import bootstrap_central_database


bootstrap_central_database()

app = FastAPI(
    title="Mayacorp CRM",
    version="0.1.0",
    description="API SaaS multi-tenant para CRM, ERP, WhatsApp, IA, financeiro e analytics.",
    openapi_tags=[
        {"name": "health", "description": "Healthcheck e operacao basica."},
        {"name": "central-auth", "description": "Autenticacao e gestao da conta central."},
        {"name": "central-saas", "description": "Administracao SaaS, tenants e dashboards centrais."},
        {"name": "tenant-auth", "description": "Autenticacao do workspace."},
        {"name": "tenant-users", "description": "Usuarios, papeis e permissoes do tenant."},
        {"name": "crm", "description": "Leads, clients e operacoes comerciais."},
        {"name": "finance", "description": "Financeiro, categorias, centros de custo e dashboards."},
        {"name": "documents", "description": "Propostas, contratos e assinatura."},
        {"name": "whatsapp", "description": "Sessao, mensagens e inbox."},
        {"name": "ai", "description": "Configuracao e uso de IA."},
        {"name": "analytics", "description": "Analytics central e snapshots."},
        {"name": "marketplace", "description": "Integracoes de marketplace."},
        {"name": "storage", "description": "Storage por workspace e acesso assinado."},
        {"name": "leadradar", "description": "Captura e processamento de lead radar."},
    ],
)
app.add_middleware(TenantResolutionMiddleware)
app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent / "static"), name="static")
app.include_router(router)
app.include_router(panel_router)
