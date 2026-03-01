# PostgreSQL em outra porta (sem Docker)

No Debian/Ubuntu, uma segunda instancia do PostgreSQL instalada via `apt` e criada como um novo cluster da mesma versao.

Exemplo com PostgreSQL 15 na porta `5434`:

```bash
sudo pg_createcluster 15 mayacorp --port=5434
sudo pg_ctlcluster 15 mayacorp start
sudo -u postgres psql -p 5434 -c "ALTER USER postgres WITH PASSWORD 'change-me';"
sudo -u postgres createdb -p 5434 mayacorp_central
```

Dados minimos para a aplicacao:

- Host: `127.0.0.1`
- Porta: `5434`
- Banco central: `mayacorp_central`
- Usuario: `postgres` ou usuario dedicado

Para criar um usuario dedicado:

```bash
sudo -u postgres psql -p 5434
CREATE ROLE mayacorp_app LOGIN PASSWORD 'change-me';
ALTER ROLE mayacorp_app CREATEDB;
ALTER DATABASE mayacorp_central OWNER TO mayacorp_app;
```
