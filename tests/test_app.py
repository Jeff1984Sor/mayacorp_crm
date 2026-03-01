from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from uuid import uuid4
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text


def load_test_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "central_test.db"
    os.environ["CENTRAL_DB_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["BOOTSTRAP_JWT_SECRET"] = "test-secret"
    os.environ["APP_ENCRYPTION_KEY"] = "test-encryption-key-12345678901234567890"

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name)

    app_module = importlib.import_module("app.main")
    return TestClient(app_module.app)


def central_auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/central/auth/login",
        json={"email": "admin@mayacorp.com", "password": "1234"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def panel_central_login(client: TestClient) -> None:
    response = client.post(
        "/admin/panel/login",
        json={"email": "admin@mayacorp.com", "password": "1234"},
    )
    assert response.status_code == 200
    assert "panel_central_token=" in response.headers.get("set-cookie", "")


def panel_data(response):
    payload = response.json()
    return payload["data"] if isinstance(payload, dict) and "data" in payload else payload


def tenant_auth_headers(client: TestClient, workspace_slug: str, email: str, password: str) -> dict[str, str]:
    response = client.post(
        f"/tenant/{workspace_slug}/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_healthcheck(tmp_path: Path) -> None:
    client = load_test_client(tmp_path)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    panel_response = client.get("/admin/panel")
    assert panel_response.status_code == 200
    assert "Mayacorp Admin Panel" in panel_response.text
    assert "Leads e Clients" in panel_response.text
    assert "Pedidos" in panel_response.text
    assert "/static/admin_panel.css" in panel_response.text
    assert "/static/admin_panel_shared.js" in panel_response.text
    assert "/static/admin_panel_constants.js" in panel_response.text
    assert "/static/admin_panel_render.js" in panel_response.text
    assert "/static/admin_panel_actions.js" in panel_response.text
    assert "/static/admin_panel.js" in panel_response.text

    shared_js_response = client.get("/static/admin_panel_shared.js")
    assert shared_js_response.status_code == 200
    assert "showToast" in shared_js_response.text
    assert "toOptionalInt" in shared_js_response.text
    assert "setPanelCache" in shared_js_response.text

    constants_js_response = client.get("/static/admin_panel_constants.js")
    assert constants_js_response.status_code == 200
    assert "contractStatuses" in constants_js_response.text

    render_js_response = client.get("/static/admin_panel_render.js")
    assert render_js_response.status_code == 200
    assert "renderSummary" in render_js_response.text
    assert "updateMessageStatus" in render_js_response.text
    assert "ordersMeta" in render_js_response.text
    assert "topMetrics" in render_js_response.text
    assert "leadsMeta" in render_js_response.text
    assert "proposalsMeta" in render_js_response.text
    assert "contractsMeta" in render_js_response.text
    assert "last_qr_code" in render_js_response.text

    actions_js_response = client.get("/static/admin_panel_actions.js")
    assert actions_js_response.status_code == 200
    assert "createContract" in actions_js_response.text
    assert "credentials: \"same-origin\"" in actions_js_response.text
    assert "loadReceivables" in actions_js_response.text
    assert "documents_page" in actions_js_response.text
    assert "messages_page" in actions_js_response.text
    assert "loadDocumentsSummary" in actions_js_response.text
    assert "loadOrdersSummary" in actions_js_response.text
    assert "loadPeopleSummary" in actions_js_response.text
    assert "loadLeadsOnly" in actions_js_response.text
    assert "loadClientsOnly" in actions_js_response.text
    assert "loadProposalsOnly" in actions_js_response.text
    assert "loadContractsOnly" in actions_js_response.text
    assert "prevProposalsPage" in actions_js_response.text
    assert "nextContractsPage" in actions_js_response.text
    assert "exportOrdersCsv" in actions_js_response.text
    assert "exportPeopleCsv" in actions_js_response.text
    assert "exportDocumentsCsv" in actions_js_response.text
    assert "exportProposalsCsv" in actions_js_response.text
    assert "exportContractsCsv" in actions_js_response.text
    assert "exportMessagesCsv" in actions_js_response.text
    assert "exportFinanceCsv" in actions_js_response.text
    assert "exportReceivablesCsv" in actions_js_response.text
    assert "exportPayablesCsv" in actions_js_response.text
    assert "people_email" in actions_js_response.text
    assert "document_sort_by" in actions_js_response.text
    assert "messageSortBy" in actions_js_response.text
    assert "financeSortBy" in actions_js_response.text
    assert "clearPanelCache" in actions_js_response.text
    assert "updateContractStatus" in actions_js_response.text
    assert "prevOrdersPage" in actions_js_response.text
    assert "nextMessagesPage" in actions_js_response.text
    assert "prevLeadsPage" in actions_js_response.text
    assert "setPanelCache" in actions_js_response.text
    assert "window.prompt(\"Novo nome do lead" not in actions_js_response.text
    assert "window.prompt(\"Novo nome do client" not in actions_js_response.text

    css_response = client.get("/static/admin_panel.css")
    assert css_response.status_code == 200
    assert ".dashboard" in css_response.text

    js_response = client.get("/static/admin_panel.js")
    assert js_response.status_code == 200
    assert "admin_panel_actions.js" in js_response.text


def test_central_create_tenant_and_dashboard(tmp_path: Path) -> None:
    client = load_test_client(tmp_path)
    headers = central_auth_headers(client)
    unique = uuid4().hex[:8]
    workspace_slug = f"acme-{tmp_path.name}-{unique}".replace("_", "-")
    admin_email = f"owner+{unique}@acme.com"

    create_response = client.post(
        "/central/tenants",
        headers=headers,
        json={
            "company_name": "Acme Ltda",
            "workspace_slug": workspace_slug,
            "company_document": "123",
            "admin_name": "Acme Admin",
                "admin_email": admin_email,
            "admin_password": "1234",
            "plan_code": "starter",
            "addon_codes": ["whatsapp"],
            "billing_day": 5,
            "discount_percent": 10,
            "generate_invoice": True,
            "issue_fiscal_document": False,
        },
    )
    assert create_response.status_code == 201

    dashboard_response = client.get("/central/dashboard", headers=headers)
    assert dashboard_response.status_code == 200
    payload = dashboard_response.json()
    assert payload["tenant_count"] == 1
    assert payload["pending_invoice_count"] == 1
    assert payload["total_invoice_amount"] > 0

    panel_central_login(client)

    panel_create_response = client.post(
        "/admin/panel/tenant",
        json={
            "company_name": "Painel Ltda",
            "workspace_slug": f"painel-{unique}",
            "admin_name": "Painel Admin",
            "admin_email": f"painel+{unique}@acme.com",
            "admin_password": "1234",
        },
    )
    assert panel_create_response.status_code == 201
    assert panel_data(panel_create_response)["workspace_slug"].startswith("painel-")


def test_tenant_role_templates_crud(tmp_path: Path) -> None:
    client = load_test_client(tmp_path)
    headers = central_auth_headers(client)
    unique = uuid4().hex[:8]
    workspace_slug = f"beta-{tmp_path.name}-{unique}".replace("_", "-")
    admin_email = f"owner+{unique}@beta.com"

    create_response = client.post(
        "/central/tenants",
        headers=headers,
        json={
            "company_name": "Beta Ltda",
            "workspace_slug": workspace_slug,
            "company_document": "456",
            "admin_name": "Beta Admin",
            "admin_email": admin_email,
            "admin_password": "1234",
            "plan_code": "starter",
            "billing_day": 10,
            "discount_percent": 0,
            "generate_invoice": False,
            "issue_fiscal_document": False,
        },
    )
    assert create_response.status_code == 201

    tenant_headers = tenant_auth_headers(client, workspace_slug, admin_email, "1234")

    list_response = client.get(f"/tenant/{workspace_slug}/roles", headers=tenant_headers)
    assert list_response.status_code == 200
    assert any(item["role_name"] == "admin" for item in list_response.json())

    upsert_response = client.post(
        f"/tenant/{workspace_slug}/roles",
        headers=tenant_headers,
        json={"role_name": "custom_sales", "permissions": {"sales.write": True}},
    )
    assert upsert_response.status_code == 201
    assert upsert_response.json()["role_name"] == "custom_sales"

    delete_response = client.delete(f"/tenant/{workspace_slug}/roles/custom_sales", headers=tenant_headers)
    assert delete_response.status_code == 204


def test_marketplace_storage_and_rbac(tmp_path: Path) -> None:
    client = load_test_client(tmp_path)
    headers = central_auth_headers(client)
    unique = uuid4().hex[:8]
    workspace_slug = f"shop-{tmp_path.name}-{unique}".replace("_", "-")
    admin_email = f"owner+{unique}@shop.com"

    create_response = client.post(
        "/central/tenants",
        headers=headers,
        json={
            "company_name": "Shop Ltda",
            "workspace_slug": workspace_slug,
            "company_document": "789",
            "admin_name": "Shop Admin",
            "admin_email": admin_email,
            "admin_password": "1234",
            "plan_code": "starter",
            "addon_codes": ["whatsapp", "analytics_plus"],
            "billing_day": 12,
            "discount_percent": 5,
            "generate_invoice": True,
            "issue_fiscal_document": False,
        },
    )
    assert create_response.status_code == 201

    tenant_headers = tenant_auth_headers(client, workspace_slug, admin_email, "1234")

    role_response = client.post(
        f"/tenant/{workspace_slug}/roles",
        headers=tenant_headers,
        json={"role_name": "limited_finance", "permissions": {"finance.write": True}},
    )
    assert role_response.status_code == 201

    user_response = client.post(
        f"/tenant/{workspace_slug}/users",
        headers=tenant_headers,
        json={
            "email": f"finance+{unique}@shop.com",
            "full_name": "Finance User",
            "password": "1234",
            "is_admin": False,
            "role": "finance",
            "permissions": {"finance.write": True},
        },
    )
    assert user_response.status_code == 201

    finance_headers = tenant_auth_headers(client, workspace_slug, f"finance+{unique}@shop.com", "1234")

    denied_marketplace = client.post(
        f"/tenant/{workspace_slug}/marketplace/webhook",
        headers=finance_headers,
        json={
            "channel": "mercado_livre",
            "external_order_id": "order-1",
            "client_name": "Cliente 1",
            "client_email": "cliente1@example.com",
            "client_phone": "5511999999999",
            "total_amount": 100.0,
            "first_due_date": "2026-03-01",
        },
    )
    assert denied_marketplace.status_code == 403

    allowed_finance = client.post(
        f"/tenant/{workspace_slug}/finance/categories",
        headers=finance_headers,
        json={"name": "Receita Extra", "entry_type": "receivable"},
    )
    assert allowed_finance.status_code == 201

    admin_marketplace = client.post(
        f"/tenant/{workspace_slug}/marketplace/webhook",
        headers=tenant_headers,
        json={
            "channel": "mercado_livre",
            "external_order_id": "order-1",
            "client_name": "Cliente 1",
            "client_email": "cliente1@example.com",
            "client_phone": "5511999999999",
            "total_amount": 100.0,
            "first_due_date": "2026-03-01",
        },
    )
    assert admin_marketplace.status_code == 201

    duplicate_marketplace = client.post(
        f"/tenant/{workspace_slug}/marketplace/webhook",
        headers=tenant_headers,
        json={
            "channel": "mercado_livre",
            "external_order_id": "order-1",
            "client_name": "Cliente 1",
            "client_email": "cliente1@example.com",
            "client_phone": "5511999999999",
            "total_amount": 100.0,
            "first_due_date": "2026-03-01",
        },
    )
    assert duplicate_marketplace.status_code == 201
    assert duplicate_marketplace.json()["id"] == admin_marketplace.json()["id"]

    upload_response = client.post(
        f"/tenant/{workspace_slug}/storage/files",
        headers=tenant_headers,
        json={"bucket": "contracts", "file_name": "demo.txt", "content": "hello world"},
    )
    assert upload_response.status_code == 201
    signed_url = upload_response.json()["signed_url"]

    signed_fetch = client.get(signed_url)
    assert signed_fetch.status_code == 200
    assert signed_fetch.text == "hello world"


def test_contract_ai_and_dashboards(tmp_path: Path) -> None:
    client = load_test_client(tmp_path)
    headers = central_auth_headers(client)
    unique = uuid4().hex[:8]
    workspace_slug = f"ops-{tmp_path.name}-{unique}".replace("_", "-")
    admin_email = f"owner+{unique}@ops.com"

    create_response = client.post(
        "/central/tenants",
        headers=headers,
        json={
            "company_name": "Ops Ltda",
            "workspace_slug": workspace_slug,
            "company_document": "321",
            "admin_name": "Ops Admin",
            "admin_email": admin_email,
            "admin_password": "1234",
            "plan_code": "starter",
            "billing_day": 15,
            "discount_percent": 0,
            "generate_invoice": False,
            "issue_fiscal_document": False,
        },
    )
    assert create_response.status_code == 201

    tenant_headers = tenant_auth_headers(client, workspace_slug, admin_email, "1234")

    client_create = client.post(
        f"/tenant/{workspace_slug}/clients",
        json={"name": "Cliente Ops", "email": "cliente.ops@example.com", "phone": "5511888888888"},
    )
    assert client_create.status_code == 201
    client_id = client_create.json()["id"]

    order_create = client.post(
        f"/tenant/{workspace_slug}/sales-orders",
        headers=tenant_headers,
        json={
            "client_id": client_id,
            "order_type": "one_time",
            "installments": 1,
            "first_due_date": "2026-03-01",
            "category": "Vendas",
            "cost_center": "Comercial",
            "items": [{"description": "Servico", "quantity": 1, "unit_price": 250}],
        },
    )
    assert order_create.status_code == 201
    order_id = order_create.json()["id"]

    contract_create = client.post(
        f"/tenant/{workspace_slug}/contracts",
        headers=tenant_headers,
        json={"client_id": client_id, "sales_order_id": order_id, "title": "Contrato Ops"},
    )
    assert contract_create.status_code == 201
    contract_id = contract_create.json()["id"]

    signed_response = client.post(
        f"/tenant/{workspace_slug}/contracts/{contract_id}/signed-file",
        headers=tenant_headers,
        json={"file_name": "signed.txt", "content": "signed-content"},
    )
    assert signed_response.status_code == 200
    assert signed_response.json()["status"] == "signed"

    ai_settings = client.put(
        "/central/ai/settings",
        headers=headers,
        json={
            "provider": "gemini",
            "api_key": "secret-key",
            "model_name": "gemini-pro",
            "monthly_request_limit": 10,
            "monthly_token_limit": 1000,
        },
    )
    assert ai_settings.status_code == 200

    ai_generate = client.post(
        "/central/ai/generate",
        headers=headers,
        json={
            "workspace_slug": workspace_slug,
            "purpose": "message",
            "prompt": "Gerar mensagem comercial",
            "estimated_tokens": 20,
        },
    )
    assert ai_generate.status_code == 200
    assert ai_generate.json()["request_count"] >= 1

    finance_dashboard = client.get(f"/tenant/{workspace_slug}/finance/dashboard", headers=tenant_headers)
    assert finance_dashboard.status_code == 200
    assert finance_dashboard.json()["receivable_total"] >= 250

    commercial_dashboard = client.get(f"/tenant/{workspace_slug}/dashboard/commercial", headers=tenant_headers)
    assert commercial_dashboard.status_code == 200
    assert commercial_dashboard.json()["sales_total"] >= 250

    panel_tenant_login = client.post(
        f"/admin/panel/{workspace_slug}/login",
        json={"email": admin_email, "password": "1234"},
    )
    assert panel_tenant_login.status_code == 200
    tenant_set_cookie = panel_tenant_login.headers.get("set-cookie", "")
    assert "panel_tenant_token=" in tenant_set_cookie or "panel_tenant_slug=" in tenant_set_cookie

    panel_health = client.get(f"/admin/panel/{workspace_slug}/health")
    assert panel_health.status_code == 200

    wrong_workspace = client.get("/admin/panel/wrong-workspace/summary")
    assert wrong_workspace.status_code == 404 or wrong_workspace.status_code == 403

    panel_lead = client.post(
        f"/admin/panel/{workspace_slug}/lead",
        json={"name": "Lead via Painel", "email": "leadpanel@example.com"},
    )
    assert panel_lead.status_code == 201
    lead_id = panel_data(panel_lead)["id"]

    panel_client = client.post(
        f"/admin/panel/{workspace_slug}/client",
        json={"name": "Client via Painel", "email": "clientpanel@example.com"},
    )
    assert panel_client.status_code == 201
    client_panel_id = panel_data(panel_client)["id"]

    panel_lead_update = client.patch(
        f"/admin/panel/{workspace_slug}/lead/{lead_id}",
        json={"name": "Lead Editado", "email": "lead2@example.com", "phone": "551100000001"},
    )
    assert panel_lead_update.status_code == 200
    assert panel_data(panel_lead_update)["name"] == "Lead Editado"

    panel_client_update = client.patch(
        f"/admin/panel/{workspace_slug}/client/{client_panel_id}",
        json={"name": "Client Editado", "email": "client2@example.com", "phone": "551100000002"},
    )
    assert panel_client_update.status_code == 200
    assert panel_data(panel_client_update)["name"] == "Client Editado"

    panel_order = client.post(
        f"/admin/panel/{workspace_slug}/sales-order",
        json={
            "title": "Pedido Painel",
            "quantity": 1,
            "unit_price": 99,
            "first_due_date": "2026-03-02",
        },
    )
    assert panel_order.status_code == 200
    order_id = panel_data(panel_order)["id"]

    panel_order_update = client.patch(
        f"/admin/panel/{workspace_slug}/sales-order/{order_id}",
        json={"status": "closed"},
    )
    assert panel_order_update.status_code == 200
    assert panel_data(panel_order_update)["status"] == "closed"

    panel_proposal = client.post(
        f"/admin/panel/{workspace_slug}/proposal",
        json={"title": "Proposta Painel", "sales_order_id": order_id},
    )
    assert panel_proposal.status_code == 200
    assert panel_data(panel_proposal)["pdf_path"]
    proposal_id = panel_data(panel_proposal)["id"]

    panel_proposal_update = client.patch(
        f"/admin/panel/{workspace_slug}/proposal/{proposal_id}",
        json={"title": "Proposta Editada", "sales_order_id": order_id},
    )
    assert panel_proposal_update.status_code == 200

    proposal_rebind = client.patch(
        f"/admin/panel/{workspace_slug}/proposal/{proposal_id}",
        json={"title": "Proposta Editada", "sales_order_id": order_id + 999},
    )
    assert proposal_rebind.status_code == 409

    panel_contract = client.post(
        f"/admin/panel/{workspace_slug}/contract",
        json={"title": "Contrato Painel", "sales_order_id": order_id},
    )
    assert panel_contract.status_code == 200
    panel_contract_id = panel_data(panel_contract)["id"]

    panel_contract_update = client.patch(
        f"/admin/panel/{workspace_slug}/contract/{panel_contract_id}",
        json={"title": "Contrato Editado", "sales_order_id": order_id},
    )
    assert panel_contract_update.status_code == 200

    panel_contract_status = client.patch(
        f"/admin/panel/{workspace_slug}/contract/{panel_contract_id}/status",
        json={"status": "sent"},
    )
    assert panel_contract_status.status_code == 200
    assert panel_data(panel_contract_status)["status"] == "sent"

    invalid_contract_status = client.patch(
        f"/admin/panel/{workspace_slug}/contract/{panel_contract_id}/status",
        json={"status": "not-valid"},
    )
    assert invalid_contract_status.status_code == 422

    panel_sign = client.post(
        f"/admin/panel/{workspace_slug}/contract/sign",
        json={
            "contract_id": panel_contract_id,
            "file_name": "painel-assinado.txt",
            "content": "assinatura painel",
        },
    )
    assert panel_sign.status_code == 200
    assert panel_data(panel_sign)["status"] == "signed"

    signed_contract_edit = client.patch(
        f"/admin/panel/{workspace_slug}/contract/{panel_contract_id}",
        json={"title": "Contrato Nao Pode", "sales_order_id": order_id},
    )
    assert signed_contract_edit.status_code == 409

    detach_contract = client.patch(
        f"/admin/panel/{workspace_slug}/contract/{panel_contract_id}",
        json={"title": "Contrato Nao Pode", "sales_order_id": None},
    )
    assert detach_contract.status_code == 409

    invalid_transition = client.patch(
        f"/admin/panel/{workspace_slug}/contract/{panel_contract_id}/status",
        json={"status": "draft"},
    )
    assert invalid_transition.status_code == 409

    documents_summary = client.get(
        f"/admin/panel/{workspace_slug}/summary/documents?documents_page=1&documents_page_size=2&document_q=Editad&contract_status=signed"
    )
    assert documents_summary.status_code == 200
    documents_payload = panel_data(documents_summary)
    assert documents_payload["proposals"]
    assert documents_payload["contracts"]
    assert documents_payload["documents_page"] == 1
    assert documents_payload["documents_page_size"] == 2
    assert documents_payload["contract_status"] == "signed"

    detach_proposal = client.patch(
        f"/admin/panel/{workspace_slug}/proposal/{proposal_id}",
        json={"title": "Proposta Solta", "sales_order_id": None},
    )
    assert detach_proposal.status_code == 409

    panel_finance = client.post(
        f"/admin/panel/{workspace_slug}/finance-category",
        json={"name": "Categoria Painel", "entry_type": "receivable"},
    )
    assert panel_finance.status_code == 201

    panel_whatsapp = client.post(
        f"/admin/panel/{workspace_slug}/whatsapp-session",
        json={"provider_session_id": "panel-session"},
    )
    assert panel_whatsapp.status_code == 200
    assert panel_data(panel_whatsapp)["status"] == "connecting"

    panel_whatsapp_status = client.patch(
        f"/admin/panel/{workspace_slug}/whatsapp-session/status",
        json={"status": "connected"},
    )
    assert panel_whatsapp_status.status_code == 200
    assert panel_data(panel_whatsapp_status)["status"] == "connected"

    panel_receivable = client.post(
        f"/admin/panel/{workspace_slug}/finance/receivable",
        json={"amount": 80, "due_date": "2026-03-10", "category": "Mensalidades", "cost_center": "Comercial"},
    )
    assert panel_receivable.status_code == 201
    receivable_id = panel_data(panel_receivable)["id"]

    panel_receivable_update = client.patch(
        f"/admin/panel/{workspace_slug}/finance/receivable/{receivable_id}",
        json={"status": "paid"},
    )
    assert panel_receivable_update.status_code == 200
    assert panel_data(panel_receivable_update)["status"] == "paid"

    panel_payable = client.post(
        f"/admin/panel/{workspace_slug}/finance/payable",
        json={"amount": 40, "due_date": "2026-03-11", "category": "Operacional", "cost_center": "Operacoes"},
    )
    assert panel_payable.status_code == 201
    payable_id = panel_data(panel_payable)["id"]

    panel_whatsapp_send = client.post(
        f"/admin/panel/{workspace_slug}/whatsapp/send",
        json={"body": "Mensagem painel", "lead_id": lead_id},
    )
    assert panel_whatsapp_send.status_code == 201
    message_id = panel_data(panel_whatsapp_send)["message_id"]
    assert panel_data(panel_whatsapp_send)["status"] == "sending"

    panel_message_update = client.patch(
        f"/admin/panel/{workspace_slug}/message/{message_id}",
        json={"status": "read"},
    )
    assert panel_message_update.status_code == 200
    assert panel_data(panel_message_update)["status"] == "read"

    messages_summary = client.get(
        f"/admin/panel/{workspace_slug}/summary/messages?messages_page=1&messages_page_size=2&message_status=read&message_direction=outbound&sort_by=status&sort_dir=asc"
    )
    assert messages_summary.status_code == 200
    messages_payload = panel_data(messages_summary)
    assert messages_payload["messages"]
    assert messages_payload["messages_page"] == 1
    assert messages_payload["messages_page_size"] == 2
    assert messages_payload["message_status"] == "read"
    assert messages_payload["sort_by"] == "status"

    orders_summary = client.get(
        f"/admin/panel/{workspace_slug}/summary/orders?page=1&page_size=2&order_status=closed&sort_by=total_amount&sort_dir=desc"
    )
    assert orders_summary.status_code == 200
    orders_payload = panel_data(orders_summary)
    assert orders_payload["sales_orders"]
    assert all(item["status"] == "closed" for item in orders_payload["sales_orders"])
    assert orders_payload["order_status"] == "closed"

    people_summary = client.get(
        f"/admin/panel/{workspace_slug}/summary/people?leads_page=1&leads_page_size=1&clients_page=1&clients_page_size=1&q=Editado&email=example.com&phone=5511&sort_by=name&sort_dir=asc"
    )
    assert people_summary.status_code == 200
    people_payload = panel_data(people_summary)
    assert people_payload["leads"]["items"]
    assert people_payload["clients"]["items"]
    assert people_payload["leads"]["page_size"] == 1
    assert people_payload["clients"]["page_size"] == 1
    assert people_payload["query"] == "Editado"
    assert people_payload["email"] == "example.com"
    assert people_payload["phone"] == "5511"
    assert people_payload["sort_by"] == "name"

    leads_summary = client.get(
        f"/admin/panel/{workspace_slug}/summary/leads?page=1&page_size=1&q=Editado&email=example.com&phone=5511&sort_by=name&sort_dir=asc"
    )
    assert leads_summary.status_code == 200
    assert panel_data(leads_summary)["items"]

    clients_summary = client.get(
        f"/admin/panel/{workspace_slug}/summary/clients?page=1&page_size=1&q=Editado&email=example.com&phone=5511&sort_by=name&sort_dir=asc"
    )
    assert clients_summary.status_code == 200
    assert panel_data(clients_summary)["items"]

    proposals_summary = client.get(
        f"/admin/panel/{workspace_slug}/summary/proposals?page=1&page_size=2&document_q=Proposta&sort_by=title&sort_dir=asc"
    )
    assert proposals_summary.status_code == 200
    proposals_only_payload = panel_data(proposals_summary)
    assert proposals_only_payload["items"]
    assert proposals_only_payload["page"] == 1

    contracts_summary = client.get(
        f"/admin/panel/{workspace_slug}/summary/contracts?page=1&page_size=2&document_q=Contrato&contract_status=signed&sort_by=title&sort_dir=asc"
    )
    assert contracts_summary.status_code == 200
    contracts_only_payload = panel_data(contracts_summary)
    assert contracts_only_payload["items"]
    assert contracts_only_payload["page"] == 1

    orders_export = client.get(f"/admin/panel/{workspace_slug}/summary/orders/export?order_status=closed")
    assert orders_export.status_code == 200
    assert "text/csv" in orders_export.headers["content-type"]
    assert "id,status,total_amount" in orders_export.text

    people_export = client.get(f"/admin/panel/{workspace_slug}/summary/people/export?q=Editado&email=example.com&phone=5511")
    assert people_export.status_code == 200
    assert "text/csv" in people_export.headers["content-type"]
    assert "kind,id,name,email,phone" in people_export.text
    assert f'{workspace_slug}-people.csv' in people_export.headers["content-disposition"]

    proposals_export = client.get(f"/admin/panel/{workspace_slug}/summary/proposals/export?document_q=Proposta")
    assert proposals_export.status_code == 200
    assert "id,title,sales_order_id,pdf_path" in proposals_export.text
    assert f'{workspace_slug}-proposals.csv' in proposals_export.headers["content-disposition"]

    contracts_export = client.get(f"/admin/panel/{workspace_slug}/summary/contracts/export?document_q=Contrato&contract_status=signed")
    assert contracts_export.status_code == 200
    assert "id,title,sales_order_id,status,signed_file_path" in contracts_export.text
    assert f'{workspace_slug}-contracts.csv' in contracts_export.headers["content-disposition"]

    messages_export = client.get(f"/admin/panel/{workspace_slug}/summary/messages/export?message_status=read&message_direction=outbound&sort_by=status")
    assert messages_export.status_code == 200
    assert "id,direction,status,body" in messages_export.text

    receivables_filtered = client.get(
        f"/admin/panel/{workspace_slug}/finance/receivables?status=paid&category=Mensalidades&due_from=2026-03-01&due_to=2026-03-31&sort_by=amount&sort_dir=desc"
    )
    assert receivables_filtered.status_code == 200
    receivables_payload = panel_data(receivables_filtered)
    assert receivables_payload["filters"]["status"] == "paid"
    assert receivables_payload["items"]
    assert receivables_payload["page"] == 1
    assert receivables_payload["page_size"] == 10
    assert receivables_payload["total"] >= 1
    assert receivables_payload["sort_by"] == "amount"

    payables_filtered = client.get(
        f"/admin/panel/{workspace_slug}/finance/payables?status=pending&category=Operacional&sort_by=category&sort_dir=asc"
    )
    assert payables_filtered.status_code == 200
    payables_payload = panel_data(payables_filtered)
    assert payables_payload["filters"]["category"] == "Operacional"
    assert payables_payload["items"]
    assert payables_payload["page"] == 1
    assert payables_payload["page_size"] == 10
    assert payables_payload["total"] >= 1
    assert payables_payload["sort_by"] == "category"

    finance_export = client.get(
        f"/admin/panel/{workspace_slug}/finance/export?entry_type=receivable&status=paid&sort_by=amount&sort_dir=desc"
    )
    assert finance_export.status_code == 200
    assert "id,amount,status,category,cost_center,due_date" in finance_export.text
    assert 'receivables.csv' in finance_export.headers["content-disposition"]

    finance_summary = client.get(f"/admin/panel/{workspace_slug}/summary/finance")
    assert finance_summary.status_code == 200
    finance_summary_payload = panel_data(finance_summary)
    assert finance_summary_payload["receivables"]
    assert finance_summary_payload["payables"]
    assert finance_summary_payload["finance"]["category_count"] >= 1

    invalid_finance_status = client.patch(
        f"/admin/panel/{workspace_slug}/finance/payable/{payable_id}",
        json={"status": "not-valid"},
    )
    assert invalid_finance_status.status_code == 422

    invalid_message_status = client.patch(
        f"/admin/panel/{workspace_slug}/message/{message_id}",
        json={"status": "not-valid"},
    )
    assert invalid_message_status.status_code == 422

    panel_summary = client.get(
        f"/admin/panel/{workspace_slug}/summary?page=1&page_size=3&leads_page=1&leads_page_size=2&clients_page=1&clients_page_size=2&documents_page=1&documents_page_size=2&messages_page=1&messages_page_size=2&document_q=Editad&contract_status=signed&order_status=closed&people_email=example.com&people_phone=5511&order_sort_by=total_amount&order_sort_dir=desc&people_sort_by=name&people_sort_dir=asc&document_sort_by=title&document_sort_dir=asc&message_status=read&message_direction=outbound"
    )
    assert panel_summary.status_code == 200
    summary_payload = panel_data(panel_summary)
    assert summary_payload["sales_orders"]
    assert all(item["status"] == "closed" for item in summary_payload["sales_orders"])
    assert summary_payload["proposals"]
    assert summary_payload["contracts"]
    assert summary_payload["leads"]
    assert summary_payload["clients"]
    assert summary_payload["receivables"]
    assert summary_payload["payables"]
    assert summary_payload["messages"]
    assert summary_payload["finance"]["category_count"] >= 1
    assert summary_payload["whatsapp"]["status"] == "connected"
    assert any(item["status"] == "read" for item in summary_payload["messages"])
    assert summary_payload["page"] == 1
    assert summary_payload["page_size"] == 3
    assert summary_payload["leads_page"] == 1
    assert summary_payload["leads_page_size"] == 2
    assert summary_payload["leads_total"] >= 1
    assert summary_payload["clients_page"] == 1
    assert summary_payload["clients_page_size"] == 2
    assert summary_payload["clients_total"] >= 1
    assert summary_payload["documents_page"] == 1
    assert summary_payload["documents_page_size"] == 2
    assert summary_payload["documents_total"] >= 1
    assert summary_payload["messages_page"] == 1
    assert summary_payload["messages_page_size"] == 2
    assert summary_payload["messages_total"] >= 1
    assert summary_payload["outbound_messages_total"] >= 1
    assert summary_payload["inbound_messages_total"] == 0
    assert summary_payload["query"] is None
    assert summary_payload["people_email"] == "example.com"
    assert summary_payload["people_phone"] == "5511"
    assert summary_payload["document_query"] == "Editad"
    assert summary_payload["contract_status"] == "signed"
    assert summary_payload["order_status"] == "closed"
    assert summary_payload["order_sort_by"] == "total_amount"
    assert summary_payload["people_sort_by"] == "name"
    assert summary_payload["document_sort_by"] == "title"
    assert summary_payload["message_status"] == "read"
    assert summary_payload["message_direction"] == "outbound"
    assert summary_payload["finance"]["payable_total"] >= 40
    assert summary_payload["finance"]["payable_pending"] >= 40

    filtered_summary = client.get(f"/admin/panel/{workspace_slug}/summary?page=1&page_size=3&q=Editado")
    assert filtered_summary.status_code == 200
    assert panel_data(filtered_summary)["query"] == "Editado"

    assert client.delete(f"/admin/panel/{workspace_slug}/proposal/{proposal_id}").status_code == 200
    assert client.delete(f"/admin/panel/{workspace_slug}/contract/{panel_contract_id}").status_code == 200
    assert client.delete(f"/admin/panel/{workspace_slug}/sales-order/{order_id}").status_code == 200
    assert client.delete(f"/admin/panel/{workspace_slug}/finance/receivable/{receivable_id}").status_code == 200
    assert client.delete(f"/admin/panel/{workspace_slug}/finance/payable/{payable_id}").status_code == 200
    assert client.delete(f"/admin/panel/{workspace_slug}/lead/{lead_id}").status_code == 200
    assert client.delete(f"/admin/panel/{workspace_slug}/client/{client_panel_id}").status_code == 200


def test_cli_command_mapping_and_download(tmp_path: Path) -> None:
    sys.modules.pop("scripts.api_client", None)
    api_client = importlib.import_module("scripts.api_client")

    with patch.object(api_client, "_call", return_value={"id": 10, "status": "signed"}) as call_mock:
        result = api_client.run_cli(
            [
                "sign-contract",
                "--workspace-slug",
                "acme",
                "--token",
                "tenant-token",
                "--contract-id",
                "10",
                "--file-name",
                "signed.txt",
                "--content",
                "signed-content",
            ]
        )
        assert "\"id\": 10" in result
        call_mock.assert_called_once_with(
            "POST",
            "http://127.0.0.1/tenant/acme/contracts/10/signed-file",
            {"file_name": "signed.txt", "content": "signed-content"},
            token="tenant-token",
        )

    with patch.object(api_client, "_call", return_value={"receivable_total": 250}) as call_mock:
        result = api_client.run_cli(
            [
                "finance-dashboard",
                "--workspace-slug",
                "acme",
                "--token",
                "tenant-token",
            ]
        )
        assert "\"receivable_total\": 250" in result
        call_mock.assert_called_once_with(
            "GET",
            "http://127.0.0.1/tenant/acme/finance/dashboard",
            token="tenant-token",
        )

    response_mock = Mock()
    response_mock.__enter__ = Mock(return_value=response_mock)
    response_mock.__exit__ = Mock(return_value=False)
    response_mock.read.return_value = b"downloaded"
    response_mock.headers.get.return_value = "text/plain"
    with patch.object(api_client.request, "urlopen", return_value=response_mock) as urlopen_mock:
        result = api_client.run_cli(["download-file", "--signed-url", "/storage/signed?path=a&token=b"])
        assert result == "downloaded"
        urlopen_mock.assert_called_once_with("http://127.0.0.1/storage/signed?path=a&token=b")


def test_tenant_migration_v3_on_legacy_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy_tenant.db"
    engine = create_engine(f"sqlite+pysqlite:///{db_path.as_posix()}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE role_templates (id INTEGER PRIMARY KEY, role_name VARCHAR(40))"))
        conn.execute(
            text(
                "CREATE TABLE marketplace_events ("
                "id INTEGER PRIMARY KEY, "
                "external_order_id VARCHAR(120), "
                "sales_order_id INTEGER)"
            )
        )

    migration_module = importlib.import_module("app.services.tenant_migrations.v2026_03_01_3")
    with engine.begin() as conn:
        migration_module.migration_2026_03_01_3(conn)

    inspector = inspect(engine)
    assert "tenant_schema_versions" in inspector.get_table_names()
    role_indexes = {idx["name"] for idx in inspector.get_indexes("role_templates")}
    marketplace_indexes = {idx["name"] for idx in inspector.get_indexes("marketplace_events")}
    assert "ix_role_templates_role_name" in role_indexes
    assert "ix_marketplace_events_external_order_id" in marketplace_indexes
