from __future__ import annotations

from app.models.tenant import AccountsPayable, AccountsReceivable, Client, Contract, Lead, Message, Proposal, SalesOrder


def serialize_sales_orders(items: list[SalesOrder]) -> list[dict]:
    return [{"id": item.id, "status": item.status, "total_amount": float(item.total_amount)} for item in items]


def serialize_documents(items: list[Proposal] | list[Contract]) -> list[dict]:
    payload: list[dict] = []
    for item in items:
        row = {"id": item.id, "title": item.title, "sales_order_id": item.sales_order_id}
        if isinstance(item, Proposal):
            row["pdf_path"] = item.pdf_path
        else:
            row["status"] = item.status
            row["signed_file_path"] = item.signed_file_path
        payload.append(row)
    return payload


def serialize_people(items: list[Lead] | list[Client]) -> list[dict]:
    return [{"id": item.id, "name": item.name, "email": item.email, "phone": item.phone} for item in items]


def serialize_finance_rows(items: list[AccountsReceivable] | list[AccountsPayable]) -> list[dict]:
    return [
        {"id": item.id, "amount": float(item.amount), "status": item.status, "category": item.category, "due_date": item.due_date.isoformat()}
        for item in items
    ]


def serialize_messages(items: list[Message]) -> list[dict]:
    return [{"id": item.id, "direction": item.direction, "status": item.status, "body": item.body} for item in items]
