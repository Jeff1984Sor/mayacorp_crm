from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from app.api.deps import tenant_session_dep
from app.models.tenant import (
    AccountsPayable,
    AccountsReceivable,
    Client,
    Contract,
    FinanceCategory,
    Lead,
    Message,
    Proposal,
    SalesOrder,
    TenantWhatsappAccount,
    User,
)
from app.panel_common import panel_response, panel_tenant_permission_dep

panel_summary_router = APIRouter(tags=["health"])


def _bounded_page(value: int, limit: int = 20) -> int:
    return max(1, min(value, limit))


def _serialize_sales_orders(items: list[SalesOrder]) -> list[dict]:
    return [{"id": item.id, "status": item.status, "total_amount": float(item.total_amount)} for item in items]


def _serialize_documents(items: list[Proposal] | list[Contract]) -> list[dict]:
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


def _serialize_people(items: list[Lead] | list[Client]) -> list[dict]:
    return [{"id": item.id, "name": item.name, "email": item.email, "phone": item.phone} for item in items]


def _serialize_finance_rows(items: list[AccountsReceivable] | list[AccountsPayable]) -> list[dict]:
    return [
        {"id": item.id, "amount": float(item.amount), "status": item.status, "category": item.category, "due_date": item.due_date.isoformat()}
        for item in items
    ]


def _serialize_messages(items: list[Message]) -> list[dict]:
    return [{"id": item.id, "direction": item.direction, "status": item.status, "body": item.body} for item in items]


def _apply_document_filters(
    proposals_query: Query,
    contracts_query: Query,
    *,
    document_q: str | None,
    contract_status: str | None,
) -> tuple[Query, Query]:
    if document_q:
        doc_like = f"%{document_q}%".lower()
        proposals_query = proposals_query.filter(func.lower(Proposal.title).like(doc_like))
        contracts_query = contracts_query.filter(func.lower(Contract.title).like(doc_like))
    if contract_status:
        contracts_query = contracts_query.filter(Contract.status == contract_status)
    return proposals_query, contracts_query


def _apply_message_filters(messages_query: Query, *, message_status: str | None, message_direction: str | None) -> Query:
    if message_status:
        messages_query = messages_query.filter(Message.status == message_status)
    if message_direction:
        messages_query = messages_query.filter(Message.direction == message_direction)
    return messages_query


def _load_finance_snapshot(session: Session) -> dict:
    categories = session.query(FinanceCategory).order_by(FinanceCategory.name.asc()).limit(10).all()
    receivables = session.query(AccountsReceivable).order_by(AccountsReceivable.id.desc()).limit(5).all()
    payables = session.query(AccountsPayable).order_by(AccountsPayable.id.desc()).limit(5).all()
    all_receivables = session.query(AccountsReceivable).all()
    receivable_total = float(sum(float(item.amount) for item in all_receivables))
    receivable_pending = float(sum(float(item.amount) for item in all_receivables if item.status == "pending"))
    return {
        "receivables": _serialize_finance_rows(receivables),
        "payables": _serialize_finance_rows(payables),
        "finance": {
            "category_count": len(categories),
            "categories": [{"id": item.id, "name": item.name, "entry_type": item.entry_type} for item in categories],
            "receivable_total": receivable_total,
            "receivable_pending": receivable_pending,
        },
    }


def _people_payload(query: Query, *, page: int, page_size: int) -> dict:
    page = _bounded_page(page)
    page_size = _bounded_page(page_size)
    offset = (page - 1) * page_size
    total = query.count()
    items = query.offset(offset).limit(page_size).all()
    return {
        "items": _serialize_people(items),
        "page": page,
        "page_size": page_size,
        "total": total,
    }


def _orders_payload(query: Query, *, page: int, page_size: int, order_status: str | None) -> dict:
    page = _bounded_page(page)
    page_size = _bounded_page(page_size)
    offset = (page - 1) * page_size
    total = query.count()
    items = query.offset(offset).limit(page_size).all()
    return {
        "sales_orders": _serialize_sales_orders(items),
        "sales_orders_total": total,
        "page": page,
        "page_size": page_size,
        "order_status": order_status,
    }


@panel_summary_router.get("/admin/panel/{workspace_slug}/summary")
def admin_panel_workspace_summary(
    workspace_slug: str,
    page: int = 1,
    page_size: int = 5,
    leads_page: int = 1,
    leads_page_size: int = 5,
    clients_page: int = 1,
    clients_page_size: int = 5,
    documents_page: int = 1,
    documents_page_size: int = 5,
    messages_page: int = 1,
    messages_page_size: int = 5,
    q: str | None = None,
    document_q: str | None = None,
    contract_status: str | None = None,
    order_status: str | None = None,
    message_status: str | None = None,
    message_direction: str | None = None,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    page = _bounded_page(page)
    page_size = _bounded_page(page_size)
    leads_page = _bounded_page(leads_page)
    leads_page_size = _bounded_page(leads_page_size)
    clients_page = _bounded_page(clients_page)
    clients_page_size = _bounded_page(clients_page_size)
    documents_page = _bounded_page(documents_page)
    documents_page_size = _bounded_page(documents_page_size)
    messages_page = _bounded_page(messages_page)
    messages_page_size = _bounded_page(messages_page_size)

    offset = (page - 1) * page_size
    leads_offset = (leads_page - 1) * leads_page_size
    clients_offset = (clients_page - 1) * clients_page_size
    documents_offset = (documents_page - 1) * documents_page_size
    messages_offset = (messages_page - 1) * messages_page_size

    sales_orders_query = session.query(SalesOrder).order_by(SalesOrder.id.desc())
    if order_status:
        sales_orders_query = sales_orders_query.filter(SalesOrder.status == order_status)
    sales_orders_total = sales_orders_query.count()
    sales_orders = sales_orders_query.offset(offset).limit(page_size).all()

    proposals_query = session.query(Proposal).order_by(Proposal.id.desc())
    contracts_query = session.query(Contract).order_by(Contract.id.desc())
    leads_query = session.query(Lead).order_by(Lead.id.desc())
    clients_query = session.query(Client).order_by(Client.id.desc())
    if q:
        lowered_q = f"%{q}%".lower()
        leads_query = leads_query.filter(func.lower(Lead.name).like(lowered_q))
        clients_query = clients_query.filter(func.lower(Client.name).like(lowered_q))
    proposals_query, contracts_query = _apply_document_filters(
        proposals_query,
        contracts_query,
        document_q=document_q or q,
        contract_status=contract_status,
    )
    proposals_total = proposals_query.count()
    contracts_total = contracts_query.count()
    proposals = proposals_query.offset(documents_offset).limit(documents_page_size).all()
    contracts = contracts_query.offset(documents_offset).limit(documents_page_size).all()
    leads_total = leads_query.count()
    clients_total = clients_query.count()
    leads = leads_query.offset(leads_offset).limit(leads_page_size).all()
    clients = clients_query.offset(clients_offset).limit(clients_page_size).all()

    whatsapp = session.query(TenantWhatsappAccount).order_by(TenantWhatsappAccount.id.asc()).first()
    messages_query = _apply_message_filters(
        session.query(Message).order_by(Message.id.desc()),
        message_status=message_status,
        message_direction=message_direction,
    )
    messages_total = messages_query.count()
    messages = messages_query.offset(messages_offset).limit(messages_page_size).all()

    finance_snapshot = _load_finance_snapshot(session)

    return panel_response(
        "Resumo carregado.",
        {
            "workspace_slug": workspace_slug,
            "sales_orders": _serialize_sales_orders(sales_orders),
            "sales_orders_total": sales_orders_total,
            "proposals": _serialize_documents(proposals),
            "contracts": _serialize_documents(contracts),
            "leads": _serialize_people(leads),
            "clients": _serialize_people(clients),
            "receivables": finance_snapshot["receivables"],
            "payables": finance_snapshot["payables"],
            "messages": _serialize_messages(messages),
            "finance": finance_snapshot["finance"],
            "whatsapp": (
                {
                    "id": whatsapp.id,
                    "provider_session_id": whatsapp.provider_session_id,
                    "status": whatsapp.status,
                    "last_qr_code": whatsapp.last_qr_code,
                }
                if whatsapp is not None
                else None
            ),
            "generated_at": datetime.now(UTC).isoformat(),
            "page": page,
            "page_size": page_size,
            "leads_page": leads_page,
            "leads_page_size": leads_page_size,
            "leads_total": leads_total,
            "clients_page": clients_page,
            "clients_page_size": clients_page_size,
            "clients_total": clients_total,
            "documents_page": documents_page,
            "documents_page_size": documents_page_size,
            "documents_total": max(proposals_total, contracts_total),
            "messages_page": messages_page,
            "messages_page_size": messages_page_size,
            "messages_total": messages_total,
            "query": q,
            "document_query": document_q,
            "contract_status": contract_status,
            "order_status": order_status,
            "message_status": message_status,
            "message_direction": message_direction,
        },
    )


@panel_summary_router.get("/admin/panel/{workspace_slug}/summary/orders")
def admin_panel_orders_summary(
    page: int = 1,
    page_size: int = 5,
    order_status: str | None = None,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    sales_orders_query = session.query(SalesOrder).order_by(SalesOrder.id.desc())
    if order_status:
        sales_orders_query = sales_orders_query.filter(SalesOrder.status == order_status)
    return panel_response(
        "Resumo de pedidos carregado.",
        _orders_payload(sales_orders_query, page=page, page_size=page_size, order_status=order_status),
    )


@panel_summary_router.get("/admin/panel/{workspace_slug}/summary/people")
def admin_panel_people_summary(
    q: str | None = None,
    leads_page: int = 1,
    leads_page_size: int = 5,
    clients_page: int = 1,
    clients_page_size: int = 5,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    leads_query = session.query(Lead).order_by(Lead.id.desc())
    clients_query = session.query(Client).order_by(Client.id.desc())
    if q:
        lowered_q = f"%{q}%".lower()
        leads_query = leads_query.filter(func.lower(Lead.name).like(lowered_q))
        clients_query = clients_query.filter(func.lower(Client.name).like(lowered_q))
    return panel_response(
        "Resumo de pessoas carregado.",
        {
            "leads": _people_payload(leads_query, page=leads_page, page_size=leads_page_size),
            "clients": _people_payload(clients_query, page=clients_page, page_size=clients_page_size),
            "query": q,
        },
    )


@panel_summary_router.get("/admin/panel/{workspace_slug}/summary/documents")
def admin_panel_documents_summary(
    documents_page: int = 1,
    documents_page_size: int = 5,
    document_q: str | None = None,
    contract_status: str | None = None,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    documents_page = _bounded_page(documents_page)
    documents_page_size = _bounded_page(documents_page_size)
    documents_offset = (documents_page - 1) * documents_page_size
    proposals_query, contracts_query = _apply_document_filters(
        session.query(Proposal).order_by(Proposal.id.desc()),
        session.query(Contract).order_by(Contract.id.desc()),
        document_q=document_q,
        contract_status=contract_status,
    )
    proposals_total = proposals_query.count()
    contracts_total = contracts_query.count()
    proposals = proposals_query.offset(documents_offset).limit(documents_page_size).all()
    contracts = contracts_query.offset(documents_offset).limit(documents_page_size).all()
    return panel_response(
        "Resumo de documentos carregado.",
        {
            "proposals": _serialize_documents(proposals),
            "contracts": _serialize_documents(contracts),
            "documents_page": documents_page,
            "documents_page_size": documents_page_size,
            "documents_total": max(proposals_total, contracts_total),
            "document_query": document_q,
            "contract_status": contract_status,
        },
    )


@panel_summary_router.get("/admin/panel/{workspace_slug}/summary/messages")
def admin_panel_messages_summary(
    messages_page: int = 1,
    messages_page_size: int = 5,
    message_status: str | None = None,
    message_direction: str | None = None,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    messages_page = _bounded_page(messages_page)
    messages_page_size = _bounded_page(messages_page_size)
    messages_offset = (messages_page - 1) * messages_page_size
    messages_query = _apply_message_filters(
        session.query(Message).order_by(Message.id.desc()),
        message_status=message_status,
        message_direction=message_direction,
    )
    messages_total = messages_query.count()
    messages = messages_query.offset(messages_offset).limit(messages_page_size).all()
    return panel_response(
        "Resumo de mensagens carregado.",
        {
            "messages": _serialize_messages(messages),
            "messages_page": messages_page,
            "messages_page_size": messages_page_size,
            "messages_total": messages_total,
            "message_status": message_status,
            "message_direction": message_direction,
        },
    )


@panel_summary_router.get("/admin/panel/{workspace_slug}/summary/finance")
def admin_panel_finance_summary(
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("finance.write")),
) -> dict:
    return panel_response("Resumo financeiro carregado.", _load_finance_snapshot(session))
