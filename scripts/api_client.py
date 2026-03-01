from __future__ import annotations

import argparse
import json
from pathlib import Path
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


def _parse_sales_items(raw_items: list[str]) -> list[dict]:
    items: list[dict] = []
    for raw_item in raw_items:
        try:
            description, quantity, unit_price = raw_item.split(":", 2)
            items.append(
                {
                    "description": description,
                    "quantity": float(quantity),
                    "unit_price": float(unit_price),
                }
            )
        except ValueError as exc:
            raise SystemExit(f"Invalid --item value '{raw_item}'. Use description:quantity:unit_price.") from exc
    if not items:
        raise SystemExit("At least one --item is required.")
    return items


def _read_file_content(path: str | None, inline_content: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8")
    if inline_content:
        return inline_content
    raise SystemExit("Provide --content or --content-file.")


def run_cli(argv: list[str] | None = None) -> str:
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

    tenant_login_parser = subparsers.add_parser("tenant-login")
    tenant_login_parser.add_argument("--workspace-slug", required=True)
    tenant_login_parser.add_argument("--email", required=True)
    tenant_login_parser.add_argument("--password", required=True)

    sales_order_parser = subparsers.add_parser("create-sales-order")
    sales_order_parser.add_argument("--workspace-slug", required=True)
    sales_order_parser.add_argument("--token", required=True)
    sales_order_parser.add_argument("--first-due-date", required=True)
    sales_order_parser.add_argument("--client-id", type=int)
    sales_order_parser.add_argument("--order-type", default="one_time")
    sales_order_parser.add_argument("--duration-months", type=int)
    sales_order_parser.add_argument("--installments", type=int, default=1)
    sales_order_parser.add_argument("--category")
    sales_order_parser.add_argument("--cost-center")
    sales_order_parser.add_argument(
        "--item",
        action="append",
        default=[],
        help="Format: description:quantity:unit_price. Repeat for multiple items.",
    )

    proposal_parser = subparsers.add_parser("create-proposal")
    proposal_parser.add_argument("--workspace-slug", required=True)
    proposal_parser.add_argument("--token", required=True)
    proposal_parser.add_argument("--title", required=True)
    proposal_parser.add_argument("--client-id", type=int)
    proposal_parser.add_argument("--sales-order-id", type=int)
    proposal_parser.add_argument("--template-name")
    proposal_parser.add_argument("--is-sendable", action="store_true")

    contract_parser = subparsers.add_parser("create-contract")
    contract_parser.add_argument("--workspace-slug", required=True)
    contract_parser.add_argument("--token", required=True)
    contract_parser.add_argument("--title", required=True)
    contract_parser.add_argument("--client-id", type=int)
    contract_parser.add_argument("--sales-order-id", type=int)
    contract_parser.add_argument("--template-name")

    sign_contract_parser = subparsers.add_parser("sign-contract")
    sign_contract_parser.add_argument("--workspace-slug", required=True)
    sign_contract_parser.add_argument("--token", required=True)
    sign_contract_parser.add_argument("--contract-id", required=True, type=int)
    sign_contract_parser.add_argument("--file-name", required=True)
    sign_contract_parser.add_argument("--content")
    sign_contract_parser.add_argument("--content-file")

    marketplace_parser = subparsers.add_parser("marketplace-webhook")
    marketplace_parser.add_argument("--workspace-slug", required=True)
    marketplace_parser.add_argument("--token", required=True)
    marketplace_parser.add_argument("--channel", required=True)
    marketplace_parser.add_argument("--external-order-id", required=True)
    marketplace_parser.add_argument("--client-name", required=True)
    marketplace_parser.add_argument("--client-email")
    marketplace_parser.add_argument("--client-phone")
    marketplace_parser.add_argument("--total-amount", required=True, type=float)
    marketplace_parser.add_argument("--first-due-date", required=True)

    storage_parser = subparsers.add_parser("upload-file")
    storage_parser.add_argument("--workspace-slug", required=True)
    storage_parser.add_argument("--token", required=True)
    storage_parser.add_argument("--bucket", required=True)
    storage_parser.add_argument("--file-name", required=True)
    storage_parser.add_argument("--content")
    storage_parser.add_argument("--content-file")

    signed_storage_parser = subparsers.add_parser("download-file")
    signed_storage_parser.add_argument("--signed-url", required=True)

    finance_dashboard_parser = subparsers.add_parser("finance-dashboard")
    finance_dashboard_parser.add_argument("--workspace-slug", required=True)
    finance_dashboard_parser.add_argument("--token", required=True)

    finance_category_parser = subparsers.add_parser("create-finance-category")
    finance_category_parser.add_argument("--workspace-slug", required=True)
    finance_category_parser.add_argument("--token", required=True)
    finance_category_parser.add_argument("--name", required=True)
    finance_category_parser.add_argument("--entry-type", default="both")

    args = parser.parse_args(argv)

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
    elif args.command == "tenant-health":
        result = _call(
            "GET",
            f"{args.base_url}/tenant/{args.workspace_slug}/health",
            token=args.token,
        )
    elif args.command == "tenant-login":
        result = _call(
            "POST",
            f"{args.base_url}/tenant/{args.workspace_slug}/auth/login",
            {"email": args.email, "password": args.password},
        )
    elif args.command == "create-sales-order":
        result = _call(
            "POST",
            f"{args.base_url}/tenant/{args.workspace_slug}/sales-orders",
            {
                "client_id": args.client_id,
                "order_type": args.order_type,
                "duration_months": args.duration_months,
                "installments": args.installments,
                "first_due_date": args.first_due_date,
                "category": args.category,
                "cost_center": args.cost_center,
                "items": _parse_sales_items(args.item),
            },
            token=args.token,
        )
    elif args.command == "create-proposal":
        result = _call(
            "POST",
            f"{args.base_url}/tenant/{args.workspace_slug}/proposals",
            {
                "client_id": args.client_id,
                "sales_order_id": args.sales_order_id,
                "title": args.title,
                "template_name": args.template_name,
                "is_sendable": args.is_sendable,
            },
            token=args.token,
        )
    elif args.command == "create-contract":
        result = _call(
            "POST",
            f"{args.base_url}/tenant/{args.workspace_slug}/contracts",
            {
                "client_id": args.client_id,
                "sales_order_id": args.sales_order_id,
                "title": args.title,
                "template_name": args.template_name,
            },
            token=args.token,
        )
    elif args.command == "sign-contract":
        result = _call(
            "POST",
            f"{args.base_url}/tenant/{args.workspace_slug}/contracts/{args.contract_id}/signed-file",
            {
                "file_name": args.file_name,
                "content": _read_file_content(args.content_file, args.content),
            },
            token=args.token,
        )
    elif args.command == "marketplace-webhook":
        result = _call(
            "POST",
            f"{args.base_url}/tenant/{args.workspace_slug}/marketplace/webhook",
            {
                "channel": args.channel,
                "external_order_id": args.external_order_id,
                "client_name": args.client_name,
                "client_email": args.client_email,
                "client_phone": args.client_phone,
                "total_amount": args.total_amount,
                "first_due_date": args.first_due_date,
            },
            token=args.token,
        )
    elif args.command == "finance-dashboard":
        result = _call(
            "GET",
            f"{args.base_url}/tenant/{args.workspace_slug}/finance/dashboard",
            token=args.token,
        )
    elif args.command == "create-finance-category":
        result = _call(
            "POST",
            f"{args.base_url}/tenant/{args.workspace_slug}/finance/categories",
            {"name": args.name, "entry_type": args.entry_type},
            token=args.token,
        )
    elif args.command == "upload-file":
        result = _call(
            "POST",
            f"{args.base_url}/tenant/{args.workspace_slug}/storage/files",
            {
                "bucket": args.bucket,
                "file_name": args.file_name,
                "content": _read_file_content(args.content_file, args.content),
            },
            token=args.token,
        )
    else:
        download_url = args.signed_url
        if download_url.startswith("/"):
            download_url = f"{args.base_url}{download_url}"
        with request.urlopen(download_url) as response:
            body = response.read()
            content_type = response.headers.get("Content-Type", "application/octet-stream")
        if content_type.startswith("application/json"):
            result = json.loads(body.decode("utf-8"))
        elif content_type.startswith("text/") or content_type == "application/pdf":
            result = body.decode("utf-8", errors="replace")
        else:
            result = {
                "content_type": content_type,
                "size": len(body),
            }

    return json.dumps(result, indent=2, ensure_ascii=False) if isinstance(result, dict) else result


def main() -> None:
    print(run_cli())


if __name__ == "__main__":
    main()
