from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import central_session_dep
from app.models.central import CompanyAccount, CentralAuditLog, CentralUser
from app.panel_common import PanelCompanyAccountRequest, panel_central_user_dep, panel_response

panel_accounts_router = APIRouter(tags=["health"])

ALLOWED_ACCOUNT_STAGES = {"lead", "client"}


def _ensure_account_stage(stage: str) -> str:
    if stage not in ALLOWED_ACCOUNT_STAGES:
        raise HTTPException(status_code=422, detail=f"Invalid account stage: {stage}")
    return stage


@panel_accounts_router.get("/admin/panel/accounts")
def admin_panel_list_accounts(
    _: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    accounts = session.query(CompanyAccount).order_by(CompanyAccount.updated_at.desc(), CompanyAccount.id.desc()).all()
    return panel_response(
        "Contas carregadas.",
        {
            "items": [
                {
                    "id": account.id,
                    "name": account.name,
                    "lifecycle_stage": account.lifecycle_stage,
                    "admin_email": account.admin_email,
                    "phone": account.phone,
                    "company_document": account.company_document,
                    "tenant_id": account.tenant_id,
                    "notes": account.notes,
                    "last_converted_at": account.last_converted_at.isoformat() if account.last_converted_at else None,
                    "updated_at": account.updated_at.isoformat(),
                }
                for account in accounts
            ],
            "total": len(accounts),
        },
    )


@panel_accounts_router.post("/admin/panel/account", status_code=201)
def admin_panel_create_account(
    payload: PanelCompanyAccountRequest,
    current_user: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    stage = _ensure_account_stage(payload.lifecycle_stage)
    account = CompanyAccount(
        name=payload.name,
        lifecycle_stage=stage,
        admin_email=payload.admin_email,
        phone=payload.phone,
        company_document=payload.company_document,
        notes=payload.notes,
        last_converted_at=datetime.now(UTC) if stage == "client" else None,
    )
    session.add(account)
    session.flush()
    session.add(
        CentralAuditLog(
            actor_email=current_user.email,
            action="account.created",
            target_type="company_account",
            target_id=str(account.id),
            payload={"stage": stage, "tenant_id": account.tenant_id},
        )
    )
    session.commit()
    return panel_response(
        "Conta criada.",
        {
            "id": account.id,
            "name": account.name,
            "lifecycle_stage": account.lifecycle_stage,
            "admin_email": account.admin_email,
            "tenant_id": account.tenant_id,
        },
    )


@panel_accounts_router.patch("/admin/panel/account/{account_id}")
def admin_panel_update_account(
    account_id: int,
    payload: PanelCompanyAccountRequest,
    current_user: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    account = session.query(CompanyAccount).filter(CompanyAccount.id == account_id).one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="Company account not found.")
    next_stage = _ensure_account_stage(payload.lifecycle_stage)
    if account.lifecycle_stage != "client" and next_stage == "client":
        account.last_converted_at = datetime.now(UTC)
    account.name = payload.name
    account.lifecycle_stage = next_stage
    account.admin_email = payload.admin_email
    account.phone = payload.phone
    account.company_document = payload.company_document
    account.notes = payload.notes
    session.add(
        CentralAuditLog(
            actor_email=current_user.email,
            action="account.updated",
            target_type="company_account",
            target_id=str(account.id),
            payload={"stage": next_stage, "tenant_id": account.tenant_id},
        )
    )
    session.commit()
    return panel_response(
        "Conta atualizada.",
        {
            "id": account.id,
            "name": account.name,
            "lifecycle_stage": account.lifecycle_stage,
            "admin_email": account.admin_email,
            "tenant_id": account.tenant_id,
            "last_converted_at": account.last_converted_at.isoformat() if account.last_converted_at else None,
        },
    )


@panel_accounts_router.post("/admin/panel/account/{account_id}/convert")
def admin_panel_convert_account(
    account_id: int,
    current_user: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    account = session.query(CompanyAccount).filter(CompanyAccount.id == account_id).one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="Company account not found.")
    previous_stage = account.lifecycle_stage
    if account.lifecycle_stage != "client":
        account.lifecycle_stage = "client"
        account.last_converted_at = datetime.now(UTC)
    session.add(
        CentralAuditLog(
            actor_email=current_user.email,
            action="account.converted",
            target_type="company_account",
            target_id=str(account.id),
            payload={"from_stage": previous_stage, "to_stage": account.lifecycle_stage, "tenant_id": account.tenant_id},
        )
    )
    session.commit()
    return panel_response(
        "Conta convertida para client.",
        {
            "id": account.id,
            "name": account.name,
            "lifecycle_stage": account.lifecycle_stage,
            "admin_email": account.admin_email,
            "tenant_id": account.tenant_id,
            "last_converted_at": account.last_converted_at.isoformat() if account.last_converted_at else None,
        },
    )
