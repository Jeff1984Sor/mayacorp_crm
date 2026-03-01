from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import tenant_session_dep
from app.models.tenant import Message, TenantWhatsappAccount, User
from app.panel_common import (
    PanelStatusRequest,
    PanelWhatsappSendRequest,
    PanelWhatsappSessionRequest,
    panel_response,
    panel_tenant_permission_dep,
)

panel_whatsapp_router = APIRouter(tags=["health"])


@panel_whatsapp_router.post("/admin/panel/{workspace_slug}/whatsapp-session")
def admin_panel_upsert_whatsapp_session(
    workspace_slug: str,
    payload: PanelWhatsappSessionRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("whatsapp.manage")),
) -> dict:
    account = session.query(TenantWhatsappAccount).order_by(TenantWhatsappAccount.id.asc()).first()
    if account is None:
        account = TenantWhatsappAccount(provider_session_id=payload.provider_session_id, status="connecting", last_qr_code="qr-placeholder")
        session.add(account)
    else:
        account.provider_session_id = payload.provider_session_id
        account.status = "connecting"
        account.last_qr_code = "qr-placeholder"
    session.commit()
    session.refresh(account)
    return panel_response(
        "Sessao WhatsApp atualizada.",
        {
            "id": account.id,
            "workspace_slug": workspace_slug,
            "provider_session_id": account.provider_session_id,
            "status": account.status,
            "last_qr_code": account.last_qr_code,
        },
    )


@panel_whatsapp_router.patch("/admin/panel/{workspace_slug}/whatsapp-session/status")
def admin_panel_update_whatsapp_session_status(
    payload: PanelStatusRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("whatsapp.manage")),
) -> dict:
    account = session.query(TenantWhatsappAccount).order_by(TenantWhatsappAccount.id.asc()).first()
    if account is None:
        raise HTTPException(status_code=404, detail="WhatsApp session not found.")
    account.status = payload.status
    session.commit()
    return panel_response("Status da sessao WhatsApp atualizado.", {"id": account.id, "status": account.status})


@panel_whatsapp_router.post("/admin/panel/{workspace_slug}/whatsapp/send", status_code=201)
def admin_panel_send_whatsapp(
    payload: PanelWhatsappSendRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("whatsapp.send")),
) -> dict:
    if payload.client_id is None and payload.lead_id is None:
        raise HTTPException(status_code=422, detail="client_id or lead_id is required.")
    message = Message(
        client_id=payload.client_id,
        lead_id=payload.lead_id,
        direction="outbound",
        body=payload.body,
        status="sending",
    )
    session.add(message)
    session.commit()
    session.refresh(message)
    return panel_response("Mensagem enviada para fila imediata.", {"message_id": message.id, "status": message.status})


@panel_whatsapp_router.patch("/admin/panel/{workspace_slug}/message/{message_id}")
def admin_panel_update_message_status(
    message_id: int,
    payload: PanelStatusRequest,
    session: Session = Depends(tenant_session_dep),
    _: User = Depends(panel_tenant_permission_dep("whatsapp.manage")),
) -> dict:
    message = session.query(Message).filter(Message.id == message_id).one_or_none()
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found.")
    message.status = payload.status
    session.commit()
    return panel_response("Status da mensagem atualizado.", {"id": message.id, "status": message.status})
