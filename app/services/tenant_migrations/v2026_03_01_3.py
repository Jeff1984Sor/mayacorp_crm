from __future__ import annotations

from sqlalchemy import inspect, text


def migration_2026_03_01_3(conn) -> None:
    inspector = inspect(conn)
    table_names = set(inspector.get_table_names())

    if "tenant_schema_versions" not in table_names:
        conn.execute(
            text(
                "CREATE TABLE tenant_schema_versions ("
                "id INTEGER PRIMARY KEY, "
                "version VARCHAR(40) UNIQUE, "
                "created_at TIMESTAMP, "
                "updated_at TIMESTAMP)"
            )
        )

    if "role_templates" in table_names:
        indexes = {idx["name"] for idx in inspector.get_indexes("role_templates")}
        if "ix_role_templates_role_name" not in indexes:
            conn.execute(text("CREATE UNIQUE INDEX ix_role_templates_role_name ON role_templates (role_name)"))

    if "marketplace_events" in table_names:
        indexes = {idx["name"] for idx in inspector.get_indexes("marketplace_events")}
        if "ix_marketplace_events_external_order_id" not in indexes:
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX ix_marketplace_events_external_order_id "
                    "ON marketplace_events (external_order_id)"
                )
            )
