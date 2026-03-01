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

## CLI simples

Exemplos:

```bash
python scripts/api_client.py central-login --email admin@mayacorp.com --password 1234
python scripts/api_client.py central-dashboard --token CENTRAL_TOKEN
python scripts/api_client.py create-tenant --token CENTRAL_TOKEN --company-name Acme --workspace-slug acme --admin-name Owner --admin-email owner@acme.com --admin-password 1234
python scripts/api_client.py tenant-login --workspace-slug acme --email owner@acme.com --password 1234
python scripts/api_client.py tenant-health --workspace-slug acme --token TENANT_TOKEN
python scripts/api_client.py create-sales-order --workspace-slug acme --token TENANT_TOKEN --first-due-date 2026-03-01 --item "Servico:1:250" --item "Setup:1:90"
python scripts/api_client.py create-proposal --workspace-slug acme --token TENANT_TOKEN --title "Proposta Inicial" --sales-order-id 1 --is-sendable
python scripts/api_client.py create-contract --workspace-slug acme --token TENANT_TOKEN --title "Contrato Inicial" --sales-order-id 1
python scripts/api_client.py sign-contract --workspace-slug acme --token TENANT_TOKEN --contract-id 1 --file-name assinado.txt --content "contrato assinado"
python scripts/api_client.py create-finance-category --workspace-slug acme --token TENANT_TOKEN --name "Mensalidades" --entry-type receivable
python scripts/api_client.py finance-dashboard --workspace-slug acme --token TENANT_TOKEN
python scripts/api_client.py marketplace-webhook --workspace-slug acme --token TENANT_TOKEN --channel shopee --external-order-id order-1001 --client-name Cliente --client-email cliente@acme.com --total-amount 199 --first-due-date 2026-03-01
python scripts/api_client.py upload-file --workspace-slug acme --token TENANT_TOKEN --bucket proposals --file-name proposta.txt --content "conteudo inicial"
python scripts/api_client.py download-file --signed-url "http://127.0.0.1/storage/signed?path=...&token=..."
```

## Painel minimo

Ao subir a API, acesse:

```text
http://127.0.0.1/admin/panel
```

O painel e propositalmente simples e cobre:

- login central
- consulta do dashboard central
- criacao de tenant
- login do tenant
- consulta do health do tenant
- criacao rapida de pedido

Implementacao:

- rota em `app/main.py`
- template em `app/templates/admin_panel.html`

## Documentacao funcional por modulo

- `docs/modules/crm.md`
- `docs/modules/finance.md`
- `docs/modules/whatsapp.md`
- `docs/modules/ai.md`
