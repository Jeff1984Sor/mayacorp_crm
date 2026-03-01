from __future__ import annotations

import json

from sqlalchemy import inspect, text

from app.db.base import TenantBase
from app.models.tenant import RoleTemplate, TenantSchemaVersion


TENANT_SCHEMA_VERSION = "2026.03.01.1"


DEFAULT_ROLE_TEMPLATES = {
    "admin": {
        "finance.write": True,
        "sales.write": True,
        "contracts.write": True,
        "whatsapp.manage": True,
        "whatsapp.send": True,
        "leadradar.run": True,
        "marketplace.write": True,
    },
    "manager": {
        "finance.write": True,
        "sales.write": True,
        "contracts.write": True,
        "whatsapp.manage": True,
        "whatsapp.send": True,
        "leadradar.run": True,
        "marketplace.write": True,
    },
    "sales": {
        "sales.write": True,
        "contracts.write": True,
        "whatsapp.send": True,
        "leadradar.run": True,
    },
    "finance": {
        "finance.write": True,
    },
    "support": {
        "whatsapp.send": True,
    },
}


def migrate_tenant_schema(engine) -> None:
    TenantBase.metadata.create_all(bind=engine, checkfirst=True)

    inspector = inspect(engine)
    with engine.begin() as conn:
        if "lead_radar_runs" in inspector.get_table_names():
            columns = {column["name"] for column in inspector.get_columns("lead_radar_runs")}
            if "external_run_id" not in columns:
                conn.execute(text("ALTER TABLE lead_radar_runs ADD COLUMN external_run_id VARCHAR(120)"))

        if "contracts" in inspector.get_table_names():
            columns = {column["name"] for column in inspector.get_columns("contracts")}
            if "status" not in columns:
                conn.execute(text("ALTER TABLE contracts ADD COLUMN status VARCHAR(40) DEFAULT 'draft'"))

        if "users" in inspector.get_table_names():
            columns = {column["name"] for column in inspector.get_columns("users")}
            if "role" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(40) DEFAULT 'admin'"))

        if "proposals" in inspector.get_table_names():
            columns = {column["name"] for column in inspector.get_columns("proposals")}
            if "sales_order_id" not in columns:
                conn.execute(text("ALTER TABLE proposals ADD COLUMN sales_order_id INTEGER"))

        if "contracts" in inspector.get_table_names():
            columns = {column["name"] for column in inspector.get_columns("contracts")}
            if "sales_order_id" not in columns:
                conn.execute(text("ALTER TABLE contracts ADD COLUMN sales_order_id INTEGER"))

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

        if "tenant_schema_versions" not in inspector.get_table_names():
            TenantSchemaVersion.__table__.create(bind=conn, checkfirst=True)

        if "role_templates" not in inspector.get_table_names():
            RoleTemplate.__table__.create(bind=conn, checkfirst=True)

        existing_roles = {
            row[0] for row in conn.execute(text("SELECT role_name FROM role_templates")).fetchall()
        }
        for role_name, permissions in DEFAULT_ROLE_TEMPLATES.items():
            if role_name not in existing_roles:
                conn.execute(
                    text(
                        "INSERT INTO role_templates (role_name, permissions, created_at, updated_at) "
                        "VALUES (:role_name, :permissions, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                    ),
                    {"role_name": role_name, "permissions": json.dumps(permissions)},
                )

        existing_versions = {
            row[0] for row in conn.execute(text("SELECT version FROM tenant_schema_versions")).fetchall()
        }
        if TENANT_SCHEMA_VERSION not in existing_versions:
            conn.execute(
                text(
                    "INSERT INTO tenant_schema_versions (version, created_at, updated_at) "
                    "VALUES (:version, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {"version": TENANT_SCHEMA_VERSION},
            )
