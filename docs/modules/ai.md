# AI Module

## Objetivo

Controlar IA de forma centralizada no SaaS e limitar o consumo por tenant.

## Escopo atual

- configuracao central de provider/modelo/chave
- geracao sincronica por endpoint central
- registro de uso diario
- consolidacao mensal
- reflexo no health score

## Endpoints principais

- `GET /central/ai/settings`
- `PUT /central/ai/settings`
- `POST /central/ai/generate`
- `GET /central/ai/summary/{workspace_slug}`
- `POST /central/analytics/run-daily`
- `POST /central/analytics/run-monthly`

## Fluxo recomendado

1. Configurar provider e limites no Admin Central.
2. Chamar geracao informando `workspace_slug`, `purpose` e `prompt`.
3. O backend checa os limites do mes.
4. O uso diario e persistido.
5. Analytics central consolida snapshots e pode abrir `central_tasks` para tenants em risco.

## Observacoes

- A chave de IA e criptografada em repouso com `Fernet`.
- O tenant nao recebe a chave bruta.
- A resposta atual de geracao e funcional para o backend; a integracao final com provider externo pode ser refinada depois.
