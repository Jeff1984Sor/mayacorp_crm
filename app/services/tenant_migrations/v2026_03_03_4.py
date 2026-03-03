from __future__ import annotations

from sqlalchemy import inspect, text


def migration_2026_03_03_4(conn) -> None:
    inspector = inspect(conn)

    lead_columns = {column["name"] for column in inspector.get_columns("leads")}
    if "company_account_id" not in lead_columns:
        conn.execute(text("ALTER TABLE leads ADD COLUMN company_account_id INTEGER"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_leads_company_account_id ON leads (company_account_id)"))

    client_columns = {column["name"] for column in inspector.get_columns("clients")}
    if "company_account_id" not in client_columns:
        conn.execute(text("ALTER TABLE clients ADD COLUMN company_account_id INTEGER"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_clients_company_account_id ON clients (company_account_id)"))

    sales_order_columns = {column["name"] for column in inspector.get_columns("sales_orders")}
    if "company_account_id" not in sales_order_columns:
        conn.execute(text("ALTER TABLE sales_orders ADD COLUMN company_account_id INTEGER"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sales_orders_company_account_id ON sales_orders (company_account_id)"))

    proposal_columns = {column["name"] for column in inspector.get_columns("proposals")}
    if "company_account_id" not in proposal_columns:
        conn.execute(text("ALTER TABLE proposals ADD COLUMN company_account_id INTEGER"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_proposals_company_account_id ON proposals (company_account_id)"))

    contract_columns = {column["name"] for column in inspector.get_columns("contracts")}
    if "company_account_id" not in contract_columns:
        conn.execute(text("ALTER TABLE contracts ADD COLUMN company_account_id INTEGER"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_contracts_company_account_id ON contracts (company_account_id)"))
