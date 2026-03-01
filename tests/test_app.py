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
