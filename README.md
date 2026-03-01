# mayacorp_crm

Base SaaS multi-tenant para CRM/ERP com FastAPI, SQLAlchemy 2.0 e PostgreSQL em producao.

## Stack

- Python 3.11+
- FastAPI
- SQLAlchemy 2.0
- Alembic
- Pydantic v2
- JWT com rotacao por chave central
- Bcrypt
- PostgreSQL em producao
- SQLite por padrao no desenvolvimento local

## Execucao local

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
uvicorn app.main:app --reload
```

Sem `CENTRAL_DB_URL`, a aplicacao usa `SQLite` local em `./data/central_dev.db`.

## Execucao em producao

Variaveis minimas:

- `CENTRAL_DB_URL`
- `BOOTSTRAP_JWT_SECRET`

Instalacao:

```bash
pip install -e .[prod]
python -m app.bootstrap
gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8011 app.main:app
```

## Arquitetura inicial

- 1 banco central para administracao SaaS
- 1 banco por tenant
- resolucao dinamica por `X-Workspace-Slug`
- middleware de isolamento via contexto de requisicao

## Fase 1 implementada

- configuracao central
- modelos centrais principais
- seed do admin central
- bootstrap de bancos
- endpoint de health
- endpoint basico de login central
- wizard inicial para criar tenant e banco dedicado
- arquivos de deploy (`systemd`, `nginx`) e docs operacionais
