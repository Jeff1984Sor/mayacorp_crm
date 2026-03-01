# Finance Module

## Objetivo

Dar base de contas a receber, contas a pagar, categorizacao e visao resumida do tenant.

## Entidades principais

- `accounts_receivable`
- `accounts_payable`
- `finance_categories`
- `cost_centers`
- `bank_accounts`

## Fluxo recomendado

1. Revisar categorias e centros de custo seedados no onboarding.
2. Criar ou ajustar categorias conforme a operacao.
3. Registrar contas a pagar manuais.
4. Deixar contas a receber serem criadas pelos pedidos ou criar manualmente.
5. Consultar dashboard e exportacao para conciliacao.

## Endpoints principais

- `POST /tenant/{workspace}/finance/categories`
- `GET /tenant/{workspace}/finance/categories`
- `POST /tenant/{workspace}/finance/cost-centers`
- `GET /tenant/{workspace}/finance/cost-centers`
- `POST /tenant/{workspace}/finance/accounts-receivable`
- `POST /tenant/{workspace}/finance/accounts-payable`
- `GET /tenant/{workspace}/finance/dashboard`
- `GET /tenant/{workspace}/finance/export`

## Permissoes

- `finance.write`: altera categorias, centros de custo e lancamentos

## Observacoes

- O dashboard retorna totais e pendencias.
- A exportacao atual e textual/CSV-like, suficiente para integracoes simples e auditoria basica.
