from __future__ import annotations

import argparse
import json
from urllib import request


def _call(method: str, url: str, payload: dict | None = None, token: str | None = None) -> dict | str:
    data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = request.Request(url=url, data=data, headers=headers, method=method)
    with request.urlopen(req) as response:
        body = response.read().decode("utf-8")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return body


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple API client for Mayacorp CRM")
    parser.add_argument("--base-url", default="http://127.0.0.1")

    subparsers = parser.add_subparsers(dest="command", required=True)

    login_parser = subparsers.add_parser("central-login")
    login_parser.add_argument("--email", required=True)
    login_parser.add_argument("--password", required=True)

    dashboard_parser = subparsers.add_parser("central-dashboard")
    dashboard_parser.add_argument("--token", required=True)

    tenant_parser = subparsers.add_parser("create-tenant")
    tenant_parser.add_argument("--token", required=True)
    tenant_parser.add_argument("--company-name", required=True)
    tenant_parser.add_argument("--workspace-slug", required=True)
    tenant_parser.add_argument("--admin-name", required=True)
    tenant_parser.add_argument("--admin-email", required=True)
    tenant_parser.add_argument("--admin-password", required=True)
    tenant_parser.add_argument("--plan-code", default="starter")

    health_parser = subparsers.add_parser("tenant-health")
    health_parser.add_argument("--workspace-slug", required=True)
    health_parser.add_argument("--token", required=True)

    args = parser.parse_args()

    if args.command == "central-login":
        result = _call(
            "POST",
            f"{args.base_url}/central/auth/login",
            {"email": args.email, "password": args.password},
        )
    elif args.command == "central-dashboard":
        result = _call("GET", f"{args.base_url}/central/dashboard", token=args.token)
    elif args.command == "create-tenant":
        result = _call(
            "POST",
            f"{args.base_url}/central/tenants",
            {
                "company_name": args.company_name,
                "workspace_slug": args.workspace_slug,
                "admin_name": args.admin_name,
                "admin_email": args.admin_email,
                "admin_password": args.admin_password,
                "plan_code": args.plan_code,
                "billing_day": 5,
                "discount_percent": 0,
                "generate_invoice": True,
                "issue_fiscal_document": False,
            },
            token=args.token,
        )
    else:
        result = _call(
            "GET",
            f"{args.base_url}/tenant/{args.workspace_slug}/health",
            token=args.token,
        )

    print(json.dumps(result, indent=2, ensure_ascii=False) if isinstance(result, dict) else result)


if __name__ == "__main__":
    main()
