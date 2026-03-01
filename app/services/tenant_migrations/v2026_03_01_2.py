from __future__ import annotations

from sqlalchemy import inspect, text


def migration_2026_03_01_2(conn) -> None:
    inspector = inspect(conn)

    if "users" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("users")}
        if "permissions" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN permissions JSON"))

    if "role_templates" not in inspector.get_table_names():
        conn.execute(
            text(
                "CREATE TABLE role_templates ("
                "id INTEGER PRIMARY KEY, "
                "role_name VARCHAR(40) UNIQUE, "
                "permissions JSON, "
                "created_at TIMESTAMP, "
                "updated_at TIMESTAMP)"
            )
        )

    if "marketplace_events" not in inspector.get_table_names():
        conn.execute(
            text(
                "CREATE TABLE marketplace_events ("
                "id INTEGER PRIMARY KEY, "
                "channel VARCHAR(80), "
                "external_order_id VARCHAR(120) UNIQUE, "
                "sales_order_id INTEGER, "
                "payload JSON, "
                "created_at TIMESTAMP, "
                "updated_at TIMESTAMP)"
            )
        )
