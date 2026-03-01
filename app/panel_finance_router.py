from __future__ import annotations

import csv
from datetime import date
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Query, Session

from app.api.deps import tenant_session_dep
from app.models.tenant import AccountsPayable, AccountsReceivable, FinanceCategory, User
from app.panel_common import (
    PANEL_FINANCE_STATUSES,
    PanelFinanceCategoryRequest,
    PanelFinanceEntryRequest,
    PanelStatusRequest,
    ensure_panel_status,
    panel_response,
    panel_tenant_permission_dep,
)

panel_finance_router = APIRouter(tags=["health"])


def _apply_finance_filters(
    query: Query,
    model: type[AccountsReceivable] | type[AccountsPayable],
    *,
    status: str | None,
    category: str | None,
    due_from: str | None,
    due_to: str | None,
) -> Query:
    if status:
        query = query.filter(model.status == status)
    if category:
        query = query.filter(model.category == category)
    if due_from:
        query = query.filter(model.due_date >= date.fromisoformat(due_from))
    if due_to:
        query = query.filter(model.due_date <= date.fromisoformat(due_to))
    return query


def _apply_finance_sort(
    query: Query,
    model: type[AccountsReceivable] | type[AccountsPayable],
    *,
    sort_by: str,
    sort_dir: str,
) -> Query:
    sort_attr = model.due_date
    if sort_by == "amount":
        sort_attr = model.amount
    elif sort_by == "status":
        sort_attr = model.status
    elif sort_by == "category":
        sort_attr = model.category
    elif sort_by == "id":
        sort_attr = model.id
    return query.order_by(sort_attr.asc() if sort_dir == "asc" else sort_attr.desc(), model.id.asc())


def _serialize_finance_entries(items: list[AccountsReceivable] | list[AccountsPayable]) -> list[dict]:
    return [
        {
            "id": item.id,
            "amount": float(item.amount),
            "status": item.status,
            "category": item.category,
            "cost_center": item.cost_center,
            "due_date": item.due_date.isoformat(),
        }
        for item in items
    ]


def _csv_response(fieldnames: list[str], rows: list[dict], filename: str) -> PlainTextResponse:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    response = PlainTextResponse(buffer.getvalue(), media_type="text/csv")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@panel_finance_router.post("/admin/panel/{workspace_slug}/finance-category", status_code=201)
def admin_panel_create_finance_category(
    workspace_slug: str,
    payload: PanelFinanceCategoryRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("finance.write")),
) -> dict:
    category = FinanceCategory(name=payload.name, entry_type=payload.entry_type)
    session.add(category)
    session.commit()
    session.refresh(category)
    return panel_response(
        "Categoria criada.",
        {"id": category.id, "name": category.name, "entry_type": category.entry_type, "workspace_slug": workspace_slug},
    )


@panel_finance_router.get("/admin/panel/{workspace_slug}/finance/receivables")
def admin_panel_list_receivables(
    status: str | None = None,
    category: str | None = None,
    due_from: str | None = None,
    due_to: str | None = None,
    sort_by: str = "due_date",
    sort_dir: str = "asc",
    page: int = 1,
    page_size: int = 10,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("finance.write")),
) -> dict:
    page = max(page, 1)
    page_size = max(1, min(page_size, 50))
    offset = (page - 1) * page_size
    query = _apply_finance_filters(session.query(AccountsReceivable), AccountsReceivable, status=status, category=category, due_from=due_from, due_to=due_to)
    query = _apply_finance_sort(query, AccountsReceivable, sort_by=sort_by, sort_dir=sort_dir)
    total = query.count()
    items = query.offset(offset).limit(page_size).all()
    return panel_response(
        "Contas a receber carregadas.",
        {
            "items": _serialize_finance_entries(items),
            "total": total,
            "page": page,
            "page_size": page_size,
            "filters": {"status": status, "category": category, "due_from": due_from, "due_to": due_to},
            "sort_by": sort_by,
            "sort_dir": sort_dir,
        },
    )


@panel_finance_router.get("/admin/panel/{workspace_slug}/finance/payables")
def admin_panel_list_payables(
    status: str | None = None,
    category: str | None = None,
    due_from: str | None = None,
    due_to: str | None = None,
    sort_by: str = "due_date",
    sort_dir: str = "asc",
    page: int = 1,
    page_size: int = 10,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("finance.write")),
) -> dict:
    page = max(page, 1)
    page_size = max(1, min(page_size, 50))
    offset = (page - 1) * page_size
    query = _apply_finance_filters(session.query(AccountsPayable), AccountsPayable, status=status, category=category, due_from=due_from, due_to=due_to)
    query = _apply_finance_sort(query, AccountsPayable, sort_by=sort_by, sort_dir=sort_dir)
    total = query.count()
    items = query.offset(offset).limit(page_size).all()
    return panel_response(
        "Contas a pagar carregadas.",
        {
            "items": _serialize_finance_entries(items),
            "total": total,
            "page": page,
            "page_size": page_size,
            "filters": {"status": status, "category": category, "due_from": due_from, "due_to": due_to},
            "sort_by": sort_by,
            "sort_dir": sort_dir,
        },
    )


@panel_finance_router.get("/admin/panel/{workspace_slug}/finance/export")
def admin_panel_export_finance(
    entry_type: str = "receivable",
    status: str | None = None,
    category: str | None = None,
    due_from: str | None = None,
    due_to: str | None = None,
    sort_by: str = "due_date",
    sort_dir: str = "asc",
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("finance.write")),
) -> PlainTextResponse:
    model = AccountsReceivable if entry_type != "payable" else AccountsPayable
    query = _apply_finance_filters(session.query(model), model, status=status, category=category, due_from=due_from, due_to=due_to)
    query = _apply_finance_sort(query, model, sort_by=sort_by, sort_dir=sort_dir)
    rows = _serialize_finance_entries(query.limit(200).all())
    return _csv_response(["id", "amount", "status", "category", "cost_center", "due_date"], rows, f"{entry_type}s.csv")


@panel_finance_router.post("/admin/panel/{workspace_slug}/finance/receivable", status_code=201)
def admin_panel_create_receivable(
    payload: PanelFinanceEntryRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("finance.write")),
) -> dict:
    entry_status = ensure_panel_status(payload.status, PANEL_FINANCE_STATUSES, "finance")
    entry = AccountsReceivable(
        due_date=date.fromisoformat(payload.due_date),
        amount=payload.amount,
        status=entry_status,
        category=payload.category,
        cost_center=payload.cost_center,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return panel_response("Conta a receber criada.", {"id": entry.id, "status": entry.status, "amount": float(entry.amount)})


@panel_finance_router.patch("/admin/panel/{workspace_slug}/finance/receivable/{entry_id}")
def admin_panel_update_receivable(
    entry_id: int,
    payload: PanelStatusRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("finance.write")),
) -> dict:
    entry = session.query(AccountsReceivable).filter(AccountsReceivable.id == entry_id).one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Accounts receivable not found.")
    entry.status = ensure_panel_status(payload.status, PANEL_FINANCE_STATUSES, "finance")
    session.commit()
    return panel_response("Conta a receber atualizada.", {"id": entry.id, "status": entry.status})


@panel_finance_router.delete("/admin/panel/{workspace_slug}/finance/receivable/{entry_id}")
def admin_panel_delete_receivable(
    entry_id: int,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("finance.write")),
) -> dict:
    entry = session.query(AccountsReceivable).filter(AccountsReceivable.id == entry_id).one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Accounts receivable not found.")
    session.delete(entry)
    session.commit()
    return panel_response("Conta a receber removida.", {"id": entry_id, "status": "deleted"})


@panel_finance_router.post("/admin/panel/{workspace_slug}/finance/payable", status_code=201)
def admin_panel_create_payable(
    payload: PanelFinanceEntryRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("finance.write")),
) -> dict:
    entry_status = ensure_panel_status(payload.status, PANEL_FINANCE_STATUSES, "finance")
    entry = AccountsPayable(
        due_date=date.fromisoformat(payload.due_date),
        amount=payload.amount,
        status=entry_status,
        category=payload.category,
        cost_center=payload.cost_center,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return panel_response("Conta a pagar criada.", {"id": entry.id, "status": entry.status, "amount": float(entry.amount)})


@panel_finance_router.patch("/admin/panel/{workspace_slug}/finance/payable/{entry_id}")
def admin_panel_update_payable(
    entry_id: int,
    payload: PanelStatusRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("finance.write")),
) -> dict:
    entry = session.query(AccountsPayable).filter(AccountsPayable.id == entry_id).one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Accounts payable not found.")
    entry.status = ensure_panel_status(payload.status, PANEL_FINANCE_STATUSES, "finance")
    session.commit()
    return panel_response("Conta a pagar atualizada.", {"id": entry.id, "status": entry.status})


@panel_finance_router.delete("/admin/panel/{workspace_slug}/finance/payable/{entry_id}")
def admin_panel_delete_payable(
    entry_id: int,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("finance.write")),
) -> dict:
    entry = session.query(AccountsPayable).filter(AccountsPayable.id == entry_id).one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Accounts payable not found.")
    session.delete(entry)
    session.commit()
    return panel_response("Conta a pagar removida.", {"id": entry_id, "status": "deleted"})
