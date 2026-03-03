from __future__ import annotations

from sqlalchemy import inspect, text


def migration_2026_03_03_5(conn) -> None:
    inspector = inspect(conn)

    sales_order_columns = {column["name"] for column in inspector.get_columns("sales_orders")}
    if "plan_id" not in sales_order_columns:
        conn.execute(text("ALTER TABLE sales_orders ADD COLUMN plan_id INTEGER"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sales_orders_plan_id ON sales_orders (plan_id)"))
    if "addon_ids" not in sales_order_columns:
        conn.execute(text("ALTER TABLE sales_orders ADD COLUMN addon_ids JSON"))
