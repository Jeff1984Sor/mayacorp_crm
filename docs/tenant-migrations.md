# Tenant schema

O schema de tenant e criado dinamicamente no provisionamento via `TenantBase.metadata.create_all`.

Escopo inicial entregue:

- `users`
- `leads`
- `clients`
- `accounts_receivable`
- `accounts_payable`
- demais tabelas base previstas para a fase seguinte

Para ambientes com PostgreSQL, o banco do tenant e criado por `CREATE DATABASE tenant_<slug>` e em seguida recebe o schema inicial automaticamente.
