from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.api.routes import router
from app.core.middleware import TenantResolutionMiddleware
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
app.include_router(router)


@app.get("/admin/panel", response_class=HTMLResponse, tags=["health"])
def admin_panel() -> str:
    return """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mayacorp CRM Panel</title>
  <style>
    :root {
      --bg: #f4f6fb;
      --card: #ffffff;
      --ink: #10243e;
      --muted: #62748a;
      --line: #d9e2ec;
      --brand: #0f766e;
      --brand-dark: #115e59;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", sans-serif;
      background: linear-gradient(135deg, #e6fffb, #f8fafc 45%, #ecfeff);
      color: var(--ink);
      min-height: 100vh;
    }
    .wrap {
      max-width: 1080px;
      margin: 0 auto;
      padding: 32px 20px 56px;
    }
    .hero {
      padding: 24px;
      border-radius: 20px;
      background: linear-gradient(140deg, #134e4a, #0f766e);
      color: #ecfeff;
      box-shadow: 0 18px 45px rgba(15, 118, 110, 0.18);
      margin-bottom: 20px;
    }
    .hero h1 { margin: 0 0 8px; font-size: 30px; }
    .hero p { margin: 0; opacity: 0.9; }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
    }
    h2 { margin: 0 0 12px; font-size: 18px; }
    label {
      display: block;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted);
      margin: 10px 0 6px;
    }
    input, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px 12px;
      font: inherit;
    }
    textarea { min-height: 110px; resize: vertical; }
    button {
      margin-top: 12px;
      border: 0;
      border-radius: 12px;
      padding: 10px 14px;
      background: var(--brand);
      color: white;
      font-weight: 600;
      cursor: pointer;
    }
    button:hover { background: var(--brand-dark); }
    .output {
      margin-top: 20px;
      background: #0f172a;
      color: #e2e8f0;
      border-radius: 18px;
      padding: 16px;
      min-height: 220px;
      white-space: pre-wrap;
      overflow: auto;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>Mayacorp Admin Panel</h1>
      <p>Painel minimo para operar login, health e consultas centrais sem curl ou CLI.</p>
    </section>
    <section class="grid">
      <div class="card">
        <h2>Login Central</h2>
        <label for="centralEmail">Email</label>
        <input id="centralEmail" value="admin@mayacorp.com">
        <label for="centralPassword">Senha</label>
        <input id="centralPassword" type="password" value="1234">
        <button onclick="centralLogin()">Entrar</button>
      </div>
      <div class="card">
        <h2>Dashboard Central</h2>
        <label for="centralToken">Token Central</label>
        <textarea id="centralToken" placeholder="Bearer token central"></textarea>
        <button onclick="centralDashboard()">Consultar</button>
      </div>
      <div class="card">
        <h2>Health do Tenant</h2>
        <label for="tenantSlug">Workspace</label>
        <input id="tenantSlug" placeholder="acme">
        <label for="tenantToken">Token Tenant</label>
        <textarea id="tenantToken" placeholder="Bearer token tenant"></textarea>
        <button onclick="tenantHealth()">Consultar</button>
      </div>
    </section>
    <pre class="output" id="output">Pronto para operar.</pre>
  </div>
  <script>
    const output = document.getElementById("output");
    async function showResult(response) {
      const contentType = response.headers.get("content-type") || "";
      const text = await response.text();
      if (contentType.includes("application/json")) {
        try {
          output.textContent = JSON.stringify(JSON.parse(text), null, 2);
          return;
        } catch (error) {}
      }
      output.textContent = text;
    }
    async function centralLogin() {
      const response = await fetch("/central/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: document.getElementById("centralEmail").value,
          password: document.getElementById("centralPassword").value
        })
      });
      await showResult(response);
    }
    async function centralDashboard() {
      const response = await fetch("/central/dashboard", {
        headers: { "Authorization": "Bearer " + document.getElementById("centralToken").value.trim() }
      });
      await showResult(response);
    }
    async function tenantHealth() {
      const slug = document.getElementById("tenantSlug").value.trim();
      const response = await fetch("/tenant/" + slug + "/health", {
        headers: { "Authorization": "Bearer " + document.getElementById("tenantToken").value.trim() }
      });
      await showResult(response);
    }
  </script>
</body>
</html>
"""
