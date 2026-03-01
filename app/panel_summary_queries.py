from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Query

from app.models.tenant import Client, Contract, Lead, Message, Proposal, SalesOrder


def bounded_page(value: int, limit: int = 20) -> int:
    return max(1, min(value, limit))


def apply_document_filters(
    proposals_query: Query,
    contracts_query: Query,
    *,
    document_q: str | None,
    contract_status: str | None,
    sort_by: str = "id",
    sort_dir: str = "desc",
) -> tuple[Query, Query]:
    if document_q:
        doc_like = f"%{document_q}%".lower()
        proposals_query = proposals_query.filter(func.lower(Proposal.title).like(doc_like))
        contracts_query = contracts_query.filter(func.lower(Contract.title).like(doc_like))
    if contract_status:
        contracts_query = contracts_query.filter(Contract.status == contract_status)
    proposals_query = apply_document_sort(proposals_query, Proposal, sort_by=sort_by, sort_dir=sort_dir)
    contracts_query = apply_document_sort(contracts_query, Contract, sort_by=sort_by, sort_dir=sort_dir)
    return proposals_query, contracts_query


def apply_message_filters(messages_query: Query, *, message_status: str | None, message_direction: str | None) -> Query:
    if message_status:
        messages_query = messages_query.filter(Message.status == message_status)
    if message_direction:
        messages_query = messages_query.filter(Message.direction == message_direction)
    return messages_query


def apply_people_filters(
    query: Query,
    model: type[Lead] | type[Client],
    *,
    q: str | None,
    email: str | None,
    phone: str | None,
    sort_by: str = "id",
    sort_dir: str = "desc",
) -> Query:
    if q:
        lowered_q = f"%{q}%".lower()
        query = query.filter(func.lower(model.name).like(lowered_q))
    if email:
        lowered_email = f"%{email}%".lower()
        query = query.filter(func.lower(model.email).like(lowered_email))
    if phone:
        query = query.filter(model.phone.like(f"%{phone}%"))
    sort_attr = model.id
    if sort_by == "name":
        sort_attr = model.name
    elif sort_by == "email":
        sort_attr = model.email
    query = query.order_by(sort_attr.asc() if sort_dir == "asc" else sort_attr.desc())
    return query


def apply_order_filters(
    query: Query,
    *,
    order_status: str | None,
    sort_by: str = "id",
    sort_dir: str = "desc",
) -> Query:
    if order_status:
        query = query.filter(SalesOrder.status == order_status)
    sort_attr = SalesOrder.id
    if sort_by == "status":
        sort_attr = SalesOrder.status
    elif sort_by == "total_amount":
        sort_attr = SalesOrder.total_amount
    query = query.order_by(sort_attr.asc() if sort_dir == "asc" else sort_attr.desc())
    return query


def apply_document_sort(query: Query, model: type[Proposal] | type[Contract], *, sort_by: str, sort_dir: str) -> Query:
    sort_attr = model.id
    if sort_by == "title":
        sort_attr = model.title
    query = query.order_by(sort_attr.asc() if sort_dir == "asc" else sort_attr.desc())
    return query
