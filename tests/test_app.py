from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

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
    workspace_slug = f"acme-{tmp_path.name}".replace("_", "-")

    create_response = client.post(
        "/central/tenants",
        headers=headers,
        json={
            "company_name": "Acme Ltda",
            "workspace_slug": workspace_slug,
            "company_document": "123",
            "admin_name": "Acme Admin",
            "admin_email": "owner@acme.com",
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
    workspace_slug = f"beta-{tmp_path.name}".replace("_", "-")
    admin_email = f"owner+{tmp_path.name}@beta.com"

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
