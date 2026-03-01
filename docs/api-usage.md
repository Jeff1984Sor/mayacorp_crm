# API Usage (VM)

## Base URL

Quando rodando local na VM via `gunicorn` + `nginx`, assuma:

```text
http://127.0.0.1
```

Ou o dominio configurado no `nginx`.

## Fluxo minimo

1. Login central

```bash
curl -X POST http://127.0.0.1/central/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"admin@mayacorp.com\",\"password\":\"1234\"}"
```

2. Criar tenant

```bash
curl -X POST http://127.0.0.1/central/tenants \
  -H "Authorization: Bearer CENTRAL_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"company_name\":\"Acme\",\"workspace_slug\":\"acme\",\"admin_name\":\"Owner\",\"admin_email\":\"owner@acme.com\",\"admin_password\":\"1234\",\"plan_code\":\"starter\",\"addon_codes\":[\"whatsapp\"],\"billing_day\":5,\"discount_percent\":0,\"generate_invoice\":true,\"issue_fiscal_document\":false}"
```

3. Login tenant

```bash
curl -X POST http://127.0.0.1/tenant/acme/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"owner@acme.com\",\"password\":\"1234\"}"
```

4. Criar pedido

```bash
curl -X POST http://127.0.0.1/tenant/acme/sales-orders \
  -H "Authorization: Bearer TENANT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"order_type\":\"one_time\",\"installments\":1,\"first_due_date\":\"2026-03-01\",\"items\":[{\"description\":\"Servico\",\"quantity\":1,\"unit_price\":250}]}"
```

## Endpoints chave

- `GET /health`
- `GET /central/dashboard`
- `POST /central/auth/change-password`
- `POST /central/auth/logout-all`
- `GET /tenant/{workspace}/health`
- `GET /tenant/{workspace}/dashboard/commercial`
- `GET /tenant/{workspace}/finance/dashboard`
- `POST /tenant/{workspace}/marketplace/webhook`
- `POST /tenant/{workspace}/storage/files`
- `GET /storage/signed`

## Testes locais

```bash
python -m pytest tests -q
```
