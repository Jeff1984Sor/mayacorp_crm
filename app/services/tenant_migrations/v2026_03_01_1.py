from __future__ import annotations

from sqlalchemy import inspect, text


def migration_2026_03_01_1(conn) -> None:
    inspector = inspect(conn)

    if "lead_radar_runs" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("lead_radar_runs")}
        if "external_run_id" not in columns:
            conn.execute(text("ALTER TABLE lead_radar_runs ADD COLUMN external_run_id VARCHAR(120)"))

    if "contracts" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("contracts")}
        if "status" not in columns:
            conn.execute(text("ALTER TABLE contracts ADD COLUMN status VARCHAR(40) DEFAULT 'draft'"))
        if "sales_order_id" not in columns:
            conn.execute(text("ALTER TABLE contracts ADD COLUMN sales_order_id INTEGER"))

    if "proposals" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("proposals")}
        if "sales_order_id" not in columns:
            conn.execute(text("ALTER TABLE proposals ADD COLUMN sales_order_id INTEGER"))

    if "users" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("users")}
        if "role" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(40) DEFAULT 'admin'"))

    if "finance_categories" not in inspector.get_table_names():
        conn.execute(
            text(
                "CREATE TABLE finance_categories ("
                "id INTEGER PRIMARY KEY, "
                "name VARCHAR(120) UNIQUE, "
                "entry_type VARCHAR(20), "
                "created_at TIMESTAMP, "
                "updated_at TIMESTAMP)"
            )
        )

    if "cost_centers" not in inspector.get_table_names():
        conn.execute(
            text(
                "CREATE TABLE cost_centers ("
                "id INTEGER PRIMARY KEY, "
                "name VARCHAR(120) UNIQUE, "
                "created_at TIMESTAMP, "
                "updated_at TIMESTAMP)"
            )
        )
