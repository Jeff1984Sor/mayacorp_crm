from __future__ import annotations

import json

from sqlalchemy import inspect, text

from app.db.base import TenantBase
from app.models.tenant import RoleTemplate, TenantSchemaVersion
from app.services.tenant_migrations import TENANT_MIGRATIONS


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
        for version, migration in TENANT_MIGRATIONS:
            if version in existing_versions:
                continue
            migration(conn)
            conn.execute(
                text(
                    "INSERT INTO tenant_schema_versions (version, created_at, updated_at) "
                    "VALUES (:version, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {"version": version},
            )
            existing_versions.add(version)
