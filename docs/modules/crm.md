# CRM Module

## Objetivo

Cobrir o fluxo operacional do tenant para cadastro, relacionamento comercial e conversao.

## Entidades principais

- `users`
- `role_templates`
- `leads`
- `clients`
- `sales_orders`
- `sales_items`
- `proposals`
- `contracts`

## Fluxo recomendado

1. Criar tenant no Admin Central.
2. Fazer login do tenant.
3. Ajustar ou criar `role_templates`.
4. Criar usuarios do tenant com `role` e `permissions`.
5. Registrar leads.
6. Converter leads em clients quando houver fechamento.
7. Criar `sales_orders` com um ou mais `sales_items`.
8. Gerar proposta ou contrato vinculado ao pedido.

## Endpoints principais

- `POST /tenant/{workspace}/auth/login`
- `GET /tenant/{workspace}/roles`
- `POST /tenant/{workspace}/users`
- `POST /tenant/{workspace}/leads`
- `POST /tenant/{workspace}/leads/{lead_id}/convert`
- `POST /tenant/{workspace}/clients`
- `POST /tenant/{workspace}/sales-orders`
- `POST /tenant/{workspace}/proposals`
- `POST /tenant/{workspace}/contracts`
- `POST /tenant/{workspace}/contracts/{contract_id}/signed-file`

## Permissoes

- `sales.write`: pedidos, clientes, leads e operacoes comerciais
- `contracts.write`: propostas e contratos

## Observacoes

- `sales_orders` geram `accounts_receivable` automaticamente.
- Contratos suportam estados controlados pelo backend: `draft`, `sent`, `signed`, `cancelled`.
