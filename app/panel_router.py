from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

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
    SalesItem,
    SalesOrder,
    TenantSchemaVersion,
    TenantWhatsappAccount,
    User,
)
from app.panel_auth_router import panel_auth_router
from app.panel_crm_router import panel_crm_router
from app.panel_finance_router import panel_finance_router
from app.panel_common import (
    panel_response,
    panel_tenant_permission_dep,
)
from app.panel_whatsapp_router import panel_whatsapp_router

panel_router = APIRouter(tags=["health"])


@panel_router.get("/admin/panel/{workspace_slug}/summary")
def admin_panel_workspace_summary(
    workspace_slug: str,
    page: int = 1,
    page_size: int = 5,
    documents_page: int = 1,
    documents_page_size: int = 5,
    messages_page: int = 1,
    messages_page_size: int = 5,
    q: str | None = None,
    document_q: str | None = None,
    contract_status: str | None = None,
    message_status: str | None = None,
    message_direction: str | None = None,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    page = max(page, 1)
    page_size = max(1, min(page_size, 20))
    offset = (page - 1) * page_size
    documents_page = max(documents_page, 1)
    documents_page_size = max(1, min(documents_page_size, 20))
    documents_offset = (documents_page - 1) * documents_page_size
    messages_page = max(messages_page, 1)
    messages_page_size = max(1, min(messages_page_size, 20))
    messages_offset = (messages_page - 1) * messages_page_size

    sales_orders = session.query(SalesOrder).order_by(SalesOrder.id.desc()).offset(offset).limit(page_size).all()
    proposals_query = session.query(Proposal).order_by(Proposal.id.desc())
    contracts_query = session.query(Contract).order_by(Contract.id.desc())
    leads_query = session.query(Lead).order_by(Lead.id.desc())
    clients_query = session.query(Client).order_by(Client.id.desc())
    if q:
        lowered_q = f"%{q}%".lower()
        leads_query = leads_query.filter(func.lower(Lead.name).like(lowered_q))
        clients_query = clients_query.filter(func.lower(Client.name).like(lowered_q))
    if q or document_q:
        doc_like = f"%{document_q or q}%".lower()
        proposals_query = proposals_query.filter(func.lower(Proposal.title).like(doc_like))
        contracts_query = contracts_query.filter(func.lower(Contract.title).like(doc_like))
    if contract_status:
        contracts_query = contracts_query.filter(Contract.status == contract_status)
    proposals_total = proposals_query.count()
    contracts_total = contracts_query.count()
    proposals = proposals_query.offset(documents_offset).limit(documents_page_size).all()
    contracts = contracts_query.offset(documents_offset).limit(documents_page_size).all()
    categories = session.query(FinanceCategory).order_by(FinanceCategory.name.asc()).limit(10).all()
    leads = leads_query.offset(offset).limit(page_size).all()
    clients = clients_query.offset(offset).limit(page_size).all()
    whatsapp = session.query(TenantWhatsappAccount).order_by(TenantWhatsappAccount.id.asc()).first()
    receivables = session.query(AccountsReceivable).order_by(AccountsReceivable.id.desc()).limit(5).all()
    payables = session.query(AccountsPayable).order_by(AccountsPayable.id.desc()).limit(5).all()
    messages_query = session.query(Message).order_by(Message.id.desc())
    if message_status:
        messages_query = messages_query.filter(Message.status == message_status)
    if message_direction:
        messages_query = messages_query.filter(Message.direction == message_direction)
    messages_total = messages_query.count()
    messages = messages_query.offset(messages_offset).limit(messages_page_size).all()
    all_receivables = session.query(AccountsReceivable).all()
    receivable_total = float(sum(float(item.amount) for item in all_receivables))
    receivable_pending = float(sum(float(item.amount) for item in all_receivables if item.status == "pending"))

    return panel_response(
        "Resumo carregado.",
        {
            "workspace_slug": workspace_slug,
            "sales_orders": [{"id": item.id, "status": item.status, "total_amount": float(item.total_amount)} for item in sales_orders],
            "proposals": [{"id": item.id, "title": item.title, "pdf_path": item.pdf_path} for item in proposals],
            "contracts": [{"id": item.id, "title": item.title, "status": item.status, "signed_file_path": item.signed_file_path} for item in contracts],
            "leads": [{"id": item.id, "name": item.name, "email": item.email, "phone": item.phone} for item in leads],
            "clients": [{"id": item.id, "name": item.name, "email": item.email, "phone": item.phone} for item in clients],
            "receivables": [
                {"id": item.id, "amount": float(item.amount), "status": item.status, "category": item.category, "due_date": item.due_date.isoformat()}
                for item in receivables
            ],
            "payables": [
                {"id": item.id, "amount": float(item.amount), "status": item.status, "category": item.category, "due_date": item.due_date.isoformat()}
                for item in payables
            ],
            "messages": [{"id": item.id, "direction": item.direction, "status": item.status, "body": item.body} for item in messages],
            "finance": {
                "category_count": len(categories),
                "categories": [{"id": item.id, "name": item.name, "entry_type": item.entry_type} for item in categories],
                "receivable_total": receivable_total,
                "receivable_pending": receivable_pending,
            },
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
            "documents_page": documents_page,
            "documents_page_size": documents_page_size,
            "documents_total": max(proposals_total, contracts_total),
            "messages_page": messages_page,
            "messages_page_size": messages_page_size,
            "messages_total": messages_total,
            "query": q,
            "document_query": document_q,
            "contract_status": contract_status,
            "message_status": message_status,
            "message_direction": message_direction,
        },
    )


@panel_router.get("/admin/panel/{workspace_slug}/summary/documents")
def admin_panel_documents_summary(
    documents_page: int = 1,
    documents_page_size: int = 5,
    document_q: str | None = None,
    contract_status: str | None = None,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    documents_page = max(documents_page, 1)
    documents_page_size = max(1, min(documents_page_size, 20))
    documents_offset = (documents_page - 1) * documents_page_size
    proposals_query = session.query(Proposal).order_by(Proposal.id.desc())
    contracts_query = session.query(Contract).order_by(Contract.id.desc())
    if document_q:
        doc_like = f"%{document_q}%".lower()
        proposals_query = proposals_query.filter(func.lower(Proposal.title).like(doc_like))
        contracts_query = contracts_query.filter(func.lower(Contract.title).like(doc_like))
    if contract_status:
        contracts_query = contracts_query.filter(Contract.status == contract_status)
    proposals_total = proposals_query.count()
    contracts_total = contracts_query.count()
    proposals = proposals_query.offset(documents_offset).limit(documents_page_size).all()
    contracts = contracts_query.offset(documents_offset).limit(documents_page_size).all()
    return panel_response(
        "Resumo de documentos carregado.",
        {
            "proposals": [{"id": item.id, "title": item.title, "pdf_path": item.pdf_path} for item in proposals],
            "contracts": [{"id": item.id, "title": item.title, "status": item.status, "signed_file_path": item.signed_file_path} for item in contracts],
            "documents_page": documents_page,
            "documents_page_size": documents_page_size,
            "documents_total": max(proposals_total, contracts_total),
            "document_query": document_q,
            "contract_status": contract_status,
        },
    )


@panel_router.get("/admin/panel/{workspace_slug}/summary/messages")
def admin_panel_messages_summary(
    messages_page: int = 1,
    messages_page_size: int = 5,
    message_status: str | None = None,
    message_direction: str | None = None,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    messages_page = max(messages_page, 1)
    messages_page_size = max(1, min(messages_page_size, 20))
    messages_offset = (messages_page - 1) * messages_page_size
    messages_query = session.query(Message).order_by(Message.id.desc())
    if message_status:
        messages_query = messages_query.filter(Message.status == message_status)
    if message_direction:
        messages_query = messages_query.filter(Message.direction == message_direction)
    messages_total = messages_query.count()
    messages = messages_query.offset(messages_offset).limit(messages_page_size).all()
    return panel_response(
        "Resumo de mensagens carregado.",
        {
            "messages": [{"id": item.id, "direction": item.direction, "status": item.status, "body": item.body} for item in messages],
            "messages_page": messages_page,
            "messages_page_size": messages_page_size,
            "messages_total": messages_total,
            "message_status": message_status,
            "message_direction": message_direction,
        },
    )


@panel_router.get("/admin/panel/{workspace_slug}/summary/finance")
def admin_panel_finance_summary(
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("finance.write")),
) -> dict:
    categories = session.query(FinanceCategory).order_by(FinanceCategory.name.asc()).limit(10).all()
    receivables = session.query(AccountsReceivable).order_by(AccountsReceivable.id.desc()).limit(5).all()
    payables = session.query(AccountsPayable).order_by(AccountsPayable.id.desc()).limit(5).all()
    all_receivables = session.query(AccountsReceivable).all()
    receivable_total = float(sum(float(item.amount) for item in all_receivables))
    receivable_pending = float(sum(float(item.amount) for item in all_receivables if item.status == "pending"))
    return panel_response(
        "Resumo financeiro carregado.",
        {
            "receivables": [
                {"id": item.id, "amount": float(item.amount), "status": item.status, "category": item.category, "due_date": item.due_date.isoformat()}
                for item in receivables
            ],
            "payables": [
                {"id": item.id, "amount": float(item.amount), "status": item.status, "category": item.category, "due_date": item.due_date.isoformat()}
                for item in payables
            ],
            "finance": {
                "category_count": len(categories),
                "categories": [{"id": item.id, "name": item.name, "entry_type": item.entry_type} for item in categories],
                "receivable_total": receivable_total,
                "receivable_pending": receivable_pending,
            },
        },
    )


panel_router.include_router(panel_auth_router)
panel_router.include_router(panel_crm_router)
panel_router.include_router(panel_finance_router)
panel_router.include_router(panel_whatsapp_router)
