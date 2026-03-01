from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import tenant_session_dep
from app.api.routes import _write_document_file, _write_signed_contract_file
from app.models.tenant import AccountsReceivable, Client, Contract, Lead, Proposal, SalesItem, SalesOrder, User
from app.panel_common import (
    PANEL_CONTRACT_STATUSES,
    PANEL_ORDER_STATUSES,
    PanelClientRequest,
    PanelContractRequest,
    PanelContractSignRequest,
    PanelLeadRequest,
    PanelProposalRequest,
    PanelSalesOrderRequest,
    PanelStatusRequest,
    ensure_panel_status,
    panel_response,
    panel_tenant_permission_dep,
)

panel_crm_router = APIRouter(tags=["health"])

ALLOWED_CONTRACT_TRANSITIONS = {
    "draft": {"sent", "cancelled"},
    "sent": {"signed", "cancelled"},
    "signed": set(),
    "cancelled": set(),
}


@panel_crm_router.post("/admin/panel/{workspace_slug}/lead", status_code=201)
def admin_panel_create_lead(
    payload: PanelLeadRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    lead = Lead(name=payload.name, email=payload.email, phone=payload.phone, source="panel")
    session.add(lead)
    session.commit()
    session.refresh(lead)
    return panel_response("Lead criado.", {"id": lead.id, "name": lead.name, "email": lead.email, "phone": lead.phone})


@panel_crm_router.patch("/admin/panel/{workspace_slug}/lead/{lead_id}")
def admin_panel_update_lead(
    lead_id: int,
    payload: PanelLeadRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    lead = session.query(Lead).filter(Lead.id == lead_id).one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    lead.name = payload.name
    lead.email = payload.email
    lead.phone = payload.phone
    session.commit()
    return panel_response("Lead atualizado.", {"id": lead.id, "name": lead.name, "email": lead.email, "phone": lead.phone})


@panel_crm_router.delete("/admin/panel/{workspace_slug}/lead/{lead_id}")
def admin_panel_delete_lead(
    lead_id: int,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    lead = session.query(Lead).filter(Lead.id == lead_id).one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    session.delete(lead)
    session.commit()
    return panel_response("Lead removido.", {"status": "deleted", "id": lead_id})


@panel_crm_router.post("/admin/panel/{workspace_slug}/client", status_code=201)
def admin_panel_create_client(
    payload: PanelClientRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    client = Client(name=payload.name, email=payload.email, phone=payload.phone)
    session.add(client)
    session.commit()
    session.refresh(client)
    return panel_response("Client criado.", {"id": client.id, "name": client.name, "email": client.email, "phone": client.phone})


@panel_crm_router.patch("/admin/panel/{workspace_slug}/client/{client_id}")
def admin_panel_update_client(
    client_id: int,
    payload: PanelClientRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    client = session.query(Client).filter(Client.id == client_id).one_or_none()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found.")
    client.name = payload.name
    client.email = payload.email
    client.phone = payload.phone
    session.commit()
    return panel_response("Client atualizado.", {"id": client.id, "name": client.name, "email": client.email, "phone": client.phone})


@panel_crm_router.delete("/admin/panel/{workspace_slug}/client/{client_id}")
def admin_panel_delete_client(
    client_id: int,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    client = session.query(Client).filter(Client.id == client_id).one_or_none()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found.")
    session.delete(client)
    session.commit()
    return panel_response("Client removido.", {"status": "deleted", "id": client_id})


@panel_crm_router.post("/admin/panel/{workspace_slug}/sales-order")
def admin_panel_create_sales_order(
    workspace_slug: str,
    payload: PanelSalesOrderRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    total_amount = (Decimal(str(payload.quantity)) * Decimal(str(payload.unit_price))).quantize(Decimal("0.01"))
    order = SalesOrder(client_id=None, order_type="one_time", duration_months=None, total_amount=total_amount, status="confirmed")
    session.add(order)
    session.flush()
    session.add(SalesItem(sales_order_id=order.id, description=payload.title, quantity=payload.quantity, unit_price=payload.unit_price))
    session.add(
        AccountsReceivable(
            sales_order_id=order.id,
            due_date=date.fromisoformat(payload.first_due_date),
            amount=total_amount,
            status="pending",
            category="Vendas",
            cost_center="Comercial",
        )
    )
    session.commit()
    return panel_response("Pedido criado.", {"id": order.id, "status": order.status, "total_amount": float(total_amount), "workspace_slug": workspace_slug})


@panel_crm_router.patch("/admin/panel/{workspace_slug}/sales-order/{order_id}")
def admin_panel_update_sales_order(
    order_id: int,
    payload: PanelStatusRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    order = session.query(SalesOrder).filter(SalesOrder.id == order_id).one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Sales order not found.")
    order.status = ensure_panel_status(payload.status, PANEL_ORDER_STATUSES, "sales order")
    session.commit()
    return panel_response("Pedido atualizado.", {"id": order.id, "status": order.status})


@panel_crm_router.delete("/admin/panel/{workspace_slug}/sales-order/{order_id}")
def admin_panel_delete_sales_order(
    order_id: int,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    order = session.query(SalesOrder).filter(SalesOrder.id == order_id).one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Sales order not found.")
    session.query(AccountsReceivable).filter(AccountsReceivable.sales_order_id == order.id).delete()
    session.query(SalesItem).filter(SalesItem.sales_order_id == order.id).delete()
    session.delete(order)
    session.commit()
    return panel_response("Pedido removido.", {"status": "deleted", "id": order_id})


@panel_crm_router.post("/admin/panel/{workspace_slug}/proposal")
def admin_panel_create_proposal(
    workspace_slug: str,
    payload: PanelProposalRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    if payload.sales_order_id is not None:
        order = session.query(SalesOrder).filter(SalesOrder.id == payload.sales_order_id).one_or_none()
        if order is None:
            raise HTTPException(status_code=404, detail="Sales order not found.")
    proposal = Proposal(title=payload.title, client_id=None, sales_order_id=payload.sales_order_id, template_name="panel-default", is_sendable=True)
    session.add(proposal)
    session.commit()
    session.refresh(proposal)
    proposal.pdf_path = _write_document_file(workspace_slug, "proposals", proposal.id, proposal.title)
    session.commit()
    return panel_response("Proposta criada.", {"id": proposal.id, "title": proposal.title, "pdf_path": proposal.pdf_path})


@panel_crm_router.patch("/admin/panel/{workspace_slug}/proposal/{proposal_id}")
def admin_panel_update_proposal(
    workspace_slug: str,
    proposal_id: int,
    payload: PanelProposalRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    proposal = session.query(Proposal).filter(Proposal.id == proposal_id).one_or_none()
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found.")
    if proposal.pdf_path and proposal.sales_order_id != payload.sales_order_id:
        raise HTTPException(status_code=409, detail="Proposal sales order cannot change after document generation.")
    if proposal.sales_order_id is not None and payload.sales_order_id is None:
        raise HTTPException(status_code=409, detail="Proposal cannot be detached from its sales order.")
    proposal.title = payload.title
    proposal.sales_order_id = payload.sales_order_id
    proposal.pdf_path = _write_document_file(workspace_slug, "proposals", proposal.id, proposal.title)
    session.commit()
    return panel_response("Proposta atualizada.", {"id": proposal.id, "title": proposal.title, "pdf_path": proposal.pdf_path})


@panel_crm_router.delete("/admin/panel/{workspace_slug}/proposal/{proposal_id}")
def admin_panel_delete_proposal(
    proposal_id: int,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("sales.write")),
) -> dict:
    proposal = session.query(Proposal).filter(Proposal.id == proposal_id).one_or_none()
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found.")
    session.delete(proposal)
    session.commit()
    return panel_response("Proposta removida.", {"status": "deleted", "id": proposal_id})


@panel_crm_router.post("/admin/panel/{workspace_slug}/contract")
def admin_panel_create_contract(
    workspace_slug: str,
    payload: PanelContractRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("contracts.write")),
) -> dict:
    if payload.sales_order_id is not None:
        order = session.query(SalesOrder).filter(SalesOrder.id == payload.sales_order_id).one_or_none()
        if order is None:
            raise HTTPException(status_code=404, detail="Sales order not found.")
    contract = Contract(title=payload.title, client_id=None, sales_order_id=payload.sales_order_id, template_name="panel-default")
    session.add(contract)
    session.commit()
    session.refresh(contract)
    contract.pdf_path = _write_document_file(workspace_slug, "contracts", contract.id, contract.title)
    session.commit()
    return panel_response("Contrato criado.", {"id": contract.id, "title": contract.title, "status": contract.status, "pdf_path": contract.pdf_path})


@panel_crm_router.patch("/admin/panel/{workspace_slug}/contract/{contract_id}")
def admin_panel_update_contract(
    workspace_slug: str,
    contract_id: int,
    payload: PanelContractRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("contracts.write")),
) -> dict:
    contract = session.query(Contract).filter(Contract.id == contract_id).one_or_none()
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found.")
    if contract.status == "signed":
        raise HTTPException(status_code=409, detail="Signed contracts cannot be edited.")
    if contract.sales_order_id is not None and payload.sales_order_id is None:
        raise HTTPException(status_code=409, detail="Contract cannot be detached from its sales order.")
    contract.title = payload.title
    contract.sales_order_id = payload.sales_order_id
    contract.pdf_path = _write_document_file(workspace_slug, "contracts", contract.id, contract.title)
    session.commit()
    return panel_response("Contrato atualizado.", {"id": contract.id, "title": contract.title, "status": contract.status, "pdf_path": contract.pdf_path})


@panel_crm_router.patch("/admin/panel/{workspace_slug}/contract/{contract_id}/status")
def admin_panel_update_contract_status(
    contract_id: int,
    payload: PanelStatusRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("contracts.write")),
) -> dict:
    contract = session.query(Contract).filter(Contract.id == contract_id).one_or_none()
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found.")
    next_status = ensure_panel_status(payload.status, PANEL_CONTRACT_STATUSES, "contract")
    if contract.status != next_status and next_status not in ALLOWED_CONTRACT_TRANSITIONS.get(contract.status, set()):
        raise HTTPException(status_code=409, detail=f"Invalid contract transition: {contract.status} -> {next_status}")
    contract.status = next_status
    session.commit()
    return panel_response("Status do contrato atualizado.", {"id": contract.id, "status": contract.status})


@panel_crm_router.delete("/admin/panel/{workspace_slug}/contract/{contract_id}")
def admin_panel_delete_contract(
    contract_id: int,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("contracts.write")),
) -> dict:
    contract = session.query(Contract).filter(Contract.id == contract_id).one_or_none()
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found.")
    session.delete(contract)
    session.commit()
    return panel_response("Contrato removido.", {"status": "deleted", "id": contract_id})


@panel_crm_router.post("/admin/panel/{workspace_slug}/contract/sign")
def admin_panel_sign_contract(
    workspace_slug: str,
    payload: PanelContractSignRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("contracts.write")),
) -> dict:
    contract = session.query(Contract).filter(Contract.id == payload.contract_id).one_or_none()
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found.")
    if contract.status == "cancelled":
        raise HTTPException(status_code=409, detail="Cancelled contracts cannot be signed.")
    contract.signed_file_path = _write_signed_contract_file(workspace_slug, contract.id, payload.file_name, payload.content)
    contract.status = "signed"
    session.commit()
    return panel_response("Contrato assinado.", {"id": contract.id, "status": contract.status, "signed_file_path": contract.signed_file_path})
