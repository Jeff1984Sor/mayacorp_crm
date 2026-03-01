from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient


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
