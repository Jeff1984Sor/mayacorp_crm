from __future__ import annotations

from datetime import UTC, datetime
import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
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
from app.panel_summary_queries import (
    apply_document_filters,
    apply_message_filters,
    apply_order_filters,
    apply_people_filters,
    bounded_page,
)
from app.panel_summary_serializers import (
    serialize_documents,
    serialize_finance_rows,
    serialize_messages,
    serialize_people,
    serialize_sales_orders,
)

panel_summary_router = APIRouter(tags=["health"])


def _load_finance_snapshot(session: Session) -> dict:
    categories = session.query(FinanceCategory).order_by(FinanceCategory.name.asc()).limit(10).all()
    receivables = session.query(AccountsReceivable).order_by(AccountsReceivable.id.desc()).limit(5).all()
    payables = session.query(AccountsPayable).order_by(AccountsPayable.id.desc()).limit(5).all()
    all_receivables = session.query(AccountsReceivable).all()
    receivable_total = float(sum(float(item.amount) for item in all_receivables))
    receivable_pending = float(sum(float(item.amount) for item in all_receivables if item.status == "pending"))
    return {
        "receivables": serialize_finance_rows(receivables),
        "payables": serialize_finance_rows(payables),
        "finance": {
            "category_count": len(categories),
            "categories": [{"id": item.id, "name": item.name, "entry_type": item.entry_type} for item in categories],
            "receivable_total": receivable_total,
            "receivable_pending": receivable_pending,
        },
    }


def _people_payload(query: Query, *, page: int, page_size: int) -> dict:
    page = bounded_page(page)
    page_size = bounded_page(page_size)
    offset = (page - 1) * page_size
    total = query.count()
    items = query.offset(offset).limit(page_size).all()
    return {
        "items": serialize_people(items),
        "page": page,
        "page_size": page_size,
        "total": total,
    }


def _orders_payload(query: Query, *, page: int, page_size: int, order_status: str | None) -> dict:
    page = bounded_page(page)
    page_size = bounded_page(page_size)
    offset = (page - 1) * page_size
    total = query.count()
    items = query.offset(offset).limit(page_size).all()
    return {
        "sales_orders": serialize_sales_orders(items),
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
    people_email: str | None = None,
    people_phone: str | None = None,
    document_q: str | None = None,
    contract_status: str | None = None,
    order_status: str | None = None,
    order_sort_by: str = "id",
    order_sort_dir: str = "desc",
    people_sort_by: str = "id",
    people_sort_dir: str = "desc",
    document_sort_by: str = "id",
    document_sort_dir: str = "desc",
    message_status: str | None = None,
    message_direction: str | None = None,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    page = bounded_page(page)
    page_size = bounded_page(page_size)
    leads_page = bounded_page(leads_page)
    leads_page_size = bounded_page(leads_page_size)
    clients_page = bounded_page(clients_page)
    clients_page_size = bounded_page(clients_page_size)
    documents_page = bounded_page(documents_page)
    documents_page_size = bounded_page(documents_page_size)
    messages_page = bounded_page(messages_page)
    messages_page_size = bounded_page(messages_page_size)

    offset = (page - 1) * page_size
    leads_offset = (leads_page - 1) * leads_page_size
    clients_offset = (clients_page - 1) * clients_page_size
    documents_offset = (documents_page - 1) * documents_page_size
    messages_offset = (messages_page - 1) * messages_page_size

    sales_orders_query = apply_order_filters(
        session.query(SalesOrder),
        order_status=order_status,
        sort_by=order_sort_by,
        sort_dir=order_sort_dir,
    )
    sales_orders_total = sales_orders_query.count()
    sales_orders = sales_orders_query.offset(offset).limit(page_size).all()

    proposals_query, contracts_query = apply_document_filters(
        session.query(Proposal),
        session.query(Contract),
        document_q=document_q or q,
        contract_status=contract_status,
        sort_by=document_sort_by,
        sort_dir=document_sort_dir,
    )
    leads_query = apply_people_filters(
        session.query(Lead),
        Lead,
        q=q,
        email=people_email,
        phone=people_phone,
        sort_by=people_sort_by,
        sort_dir=people_sort_dir,
    )
    clients_query = apply_people_filters(
        session.query(Client),
        Client,
        q=q,
        email=people_email,
        phone=people_phone,
        sort_by=people_sort_by,
        sort_dir=people_sort_dir,
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
    messages_query = apply_message_filters(
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
            "sales_orders": serialize_sales_orders(sales_orders),
            "sales_orders_total": sales_orders_total,
            "proposals": serialize_documents(proposals),
            "contracts": serialize_documents(contracts),
            "leads": serialize_people(leads),
            "clients": serialize_people(clients),
            "receivables": finance_snapshot["receivables"],
            "payables": finance_snapshot["payables"],
            "messages": serialize_messages(messages),
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
            "people_email": people_email,
            "people_phone": people_phone,
            "document_query": document_q,
            "contract_status": contract_status,
            "order_status": order_status,
            "order_sort_by": order_sort_by,
            "order_sort_dir": order_sort_dir,
            "people_sort_by": people_sort_by,
            "people_sort_dir": people_sort_dir,
            "document_sort_by": document_sort_by,
            "document_sort_dir": document_sort_dir,
            "message_status": message_status,
            "message_direction": message_direction,
        },
    )


@panel_summary_router.get("/admin/panel/{workspace_slug}/summary/orders")
def admin_panel_orders_summary(
    page: int = 1,
    page_size: int = 5,
    order_status: str | None = None,
    sort_by: str = "id",
    sort_dir: str = "desc",
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    sales_orders_query = apply_order_filters(session.query(SalesOrder), order_status=order_status, sort_by=sort_by, sort_dir=sort_dir)
    return panel_response(
        "Resumo de pedidos carregado.",
        _orders_payload(sales_orders_query, page=page, page_size=page_size, order_status=order_status),
    )


@panel_summary_router.get("/admin/panel/{workspace_slug}/summary/people")
def admin_panel_people_summary(
    q: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    sort_by: str = "id",
    sort_dir: str = "desc",
    leads_page: int = 1,
    leads_page_size: int = 5,
    clients_page: int = 1,
    clients_page_size: int = 5,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    leads_query = apply_people_filters(session.query(Lead), Lead, q=q, email=email, phone=phone, sort_by=sort_by, sort_dir=sort_dir)
    clients_query = apply_people_filters(session.query(Client), Client, q=q, email=email, phone=phone, sort_by=sort_by, sort_dir=sort_dir)
    return panel_response(
        "Resumo de pessoas carregado.",
        {
            "leads": _people_payload(leads_query, page=leads_page, page_size=leads_page_size),
            "clients": _people_payload(clients_query, page=clients_page, page_size=clients_page_size),
            "query": q,
            "email": email,
            "phone": phone,
            "sort_by": sort_by,
            "sort_dir": sort_dir,
        },
    )


@panel_summary_router.get("/admin/panel/{workspace_slug}/summary/documents")
def admin_panel_documents_summary(
    documents_page: int = 1,
    documents_page_size: int = 5,
    document_q: str | None = None,
    contract_status: str | None = None,
    sort_by: str = "id",
    sort_dir: str = "desc",
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    documents_page = bounded_page(documents_page)
    documents_page_size = bounded_page(documents_page_size)
    documents_offset = (documents_page - 1) * documents_page_size
    proposals_query, contracts_query = apply_document_filters(
        session.query(Proposal),
        session.query(Contract),
        document_q=document_q,
        contract_status=contract_status,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    proposals_total = proposals_query.count()
    contracts_total = contracts_query.count()
    proposals = proposals_query.offset(documents_offset).limit(documents_page_size).all()
    contracts = contracts_query.offset(documents_offset).limit(documents_page_size).all()
    return panel_response(
        "Resumo de documentos carregado.",
        {
            "proposals": serialize_documents(proposals),
            "contracts": serialize_documents(contracts),
            "documents_page": documents_page,
            "documents_page_size": documents_page_size,
            "documents_total": max(proposals_total, contracts_total),
            "document_query": document_q,
            "contract_status": contract_status,
            "sort_by": sort_by,
            "sort_dir": sort_dir,
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
    messages_page = bounded_page(messages_page)
    messages_page_size = bounded_page(messages_page_size)
    messages_offset = (messages_page - 1) * messages_page_size
    messages_query = apply_message_filters(
        session.query(Message).order_by(Message.id.desc()),
        message_status=message_status,
        message_direction=message_direction,
    )
    messages_total = messages_query.count()
    messages = messages_query.offset(messages_offset).limit(messages_page_size).all()
    return panel_response(
        "Resumo de mensagens carregado.",
        {
            "messages": serialize_messages(messages),
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


@panel_summary_router.get("/admin/panel/{workspace_slug}/summary/leads")
def admin_panel_leads_summary(
    q: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    sort_by: str = "id",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 5,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    query = apply_people_filters(session.query(Lead), Lead, q=q, email=email, phone=phone, sort_by=sort_by, sort_dir=sort_dir)
    return panel_response("Resumo de leads carregado.", _people_payload(query, page=page, page_size=page_size))


@panel_summary_router.get("/admin/panel/{workspace_slug}/summary/clients")
def admin_panel_clients_summary(
    q: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    sort_by: str = "id",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 5,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    query = apply_people_filters(session.query(Client), Client, q=q, email=email, phone=phone, sort_by=sort_by, sort_dir=sort_dir)
    return panel_response("Resumo de clients carregado.", _people_payload(query, page=page, page_size=page_size))


@panel_summary_router.get("/admin/panel/{workspace_slug}/summary/proposals")
def admin_panel_proposals_summary(
    page: int = 1,
    page_size: int = 5,
    document_q: str | None = None,
    sort_by: str = "id",
    sort_dir: str = "desc",
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    page = bounded_page(page)
    page_size = bounded_page(page_size)
    offset = (page - 1) * page_size
    proposals_query, _ = apply_document_filters(
        session.query(Proposal),
        session.query(Contract),
        document_q=document_q,
        contract_status=None,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    total = proposals_query.count()
    items = proposals_query.offset(offset).limit(page_size).all()
    return panel_response(
        "Resumo de propostas carregado.",
        {"items": serialize_documents(items), "page": page, "page_size": page_size, "total": total, "document_query": document_q},
    )


@panel_summary_router.get("/admin/panel/{workspace_slug}/summary/contracts")
def admin_panel_contracts_summary(
    page: int = 1,
    page_size: int = 5,
    document_q: str | None = None,
    contract_status: str | None = None,
    sort_by: str = "id",
    sort_dir: str = "desc",
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    page = bounded_page(page)
    page_size = bounded_page(page_size)
    offset = (page - 1) * page_size
    _, contracts_query = apply_document_filters(
        session.query(Proposal),
        session.query(Contract),
        document_q=document_q,
        contract_status=contract_status,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    total = contracts_query.count()
    items = contracts_query.offset(offset).limit(page_size).all()
    return panel_response(
        "Resumo de contratos carregado.",
        {
            "items": serialize_documents(items),
            "page": page,
            "page_size": page_size,
            "total": total,
            "document_query": document_q,
            "contract_status": contract_status,
        },
    )


def _csv_response(fieldnames: list[str], rows: list[dict], filename: str) -> PlainTextResponse:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    response = PlainTextResponse(buffer.getvalue(), media_type="text/csv")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@panel_summary_router.get("/admin/panel/{workspace_slug}/summary/orders/export")
def admin_panel_orders_export(
    order_status: str | None = None,
    sort_by: str = "id",
    sort_dir: str = "desc",
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> PlainTextResponse:
    query = apply_order_filters(session.query(SalesOrder), order_status=order_status, sort_by=sort_by, sort_dir=sort_dir)
    rows = serialize_sales_orders(query.limit(200).all())
    return _csv_response(["id", "status", "total_amount"], rows, "orders.csv")


@panel_summary_router.get("/admin/panel/{workspace_slug}/summary/people/export")
def admin_panel_people_export(
    q: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    sort_by: str = "id",
    sort_dir: str = "desc",
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> PlainTextResponse:
    leads = apply_people_filters(session.query(Lead), Lead, q=q, email=email, phone=phone, sort_by=sort_by, sort_dir=sort_dir).limit(100).all()
    clients = apply_people_filters(session.query(Client), Client, q=q, email=email, phone=phone, sort_by=sort_by, sort_dir=sort_dir).limit(100).all()
    rows = [{"kind": "lead", **item} for item in serialize_people(leads)] + [{"kind": "client", **item} for item in serialize_people(clients)]
    return _csv_response(["kind", "id", "name", "email", "phone"], rows, "people.csv")
