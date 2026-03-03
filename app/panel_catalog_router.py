from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import central_session_dep
from app.models.central import Addon, CentralAuditLog, CentralUser, Plan, PlanAddon, PlanPrice, Tenant, TenantSubscription
from app.panel_common import (
    PanelCatalogPlanRequest,
    PanelCatalogProductRequest,
    panel_central_user_dep,
    panel_response,
)

panel_catalog_router = APIRouter(tags=["health"])


def _normalize_code(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return cleaned.strip("-")


def _build_unique_code(session: Session, model, base_text: str, current_id: int | None = None) -> str:
    base = _normalize_code(base_text) or "item"
    candidate = base
    suffix = 2
    while True:
        query = session.query(model).filter(model.code == candidate)
        if current_id is not None:
            query = query.filter(model.id != current_id)
        if query.one_or_none() is None:
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1


def _serialize_product(product: Addon) -> dict:
    return {
        "id": product.id,
        "code": product.code,
        "name": product.name,
        "is_active": product.is_active,
        "amount": float(product.amount),
    }


def _serialize_plan(plan: Plan) -> dict:
    primary_price = sorted(plan.prices, key=lambda item: item.id)[0] if plan.prices else None
    product_links = sorted(plan_addon.addon_id for plan_addon in sessionless_plan_addons(plan))
    return {
        "id": plan.id,
        "code": plan.code,
        "name": plan.name,
        "is_active": plan.is_active,
        "product_id": product_links[0] if product_links else None,
        "amount": float(primary_price.amount) if primary_price else 0,
        "billing_cycle": primary_price.billing_cycle if primary_price else None,
        "currency": primary_price.currency if primary_price else "BRL",
    }


def sessionless_plan_addons(plan: Plan) -> list[PlanAddon]:
    return getattr(plan, "_plan_addons_cache", [])


def _load_plan_addons(session: Session, plans: list[Plan]) -> None:
    if not plans:
        return
    plan_ids = [plan.id for plan in plans]
    links = session.query(PlanAddon).filter(PlanAddon.plan_id.in_(plan_ids)).all()
    grouped: dict[int, list[PlanAddon]] = {}
    for link in links:
        grouped.setdefault(link.plan_id, []).append(link)
    for plan in plans:
        setattr(plan, "_plan_addons_cache", grouped.get(plan.id, []))


@panel_catalog_router.get("/admin/panel/catalog/products")
def admin_panel_list_products(
    _: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    items = session.query(Addon).order_by(Addon.name.asc(), Addon.id.asc()).all()
    return panel_response("Produtos carregados.", {"items": [_serialize_product(item) for item in items], "total": len(items)})


@panel_catalog_router.post("/admin/panel/catalog/product", status_code=201)
def admin_panel_create_product(
    payload: PanelCatalogProductRequest,
    current_user: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    code = _build_unique_code(session, Addon, payload.code or payload.name)
    product = Addon(code=code, name=payload.name, amount=payload.amount)
    session.add(product)
    session.flush()
    session.add(
        CentralAuditLog(
            actor_email=current_user.email,
            action="catalog.product_created",
            target_type="product",
            target_id=str(product.id),
            payload={"code": product.code},
        )
    )
    session.commit()
    return panel_response("Produto criado.", _serialize_product(product))


@panel_catalog_router.patch("/admin/panel/catalog/product/{product_id}")
def admin_panel_update_product(
    product_id: int,
    payload: PanelCatalogProductRequest,
    current_user: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    product = session.query(Addon).filter(Addon.id == product_id).one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    product.code = _build_unique_code(session, Addon, payload.code or payload.name, current_id=product_id)
    product.name = payload.name
    product.amount = payload.amount
    session.add(
        CentralAuditLog(
            actor_email=current_user.email,
            action="catalog.product_updated",
            target_type="product",
            target_id=str(product.id),
            payload={"code": product.code},
        )
    )
    session.commit()
    return panel_response("Produto atualizado.", _serialize_product(product))


@panel_catalog_router.patch("/admin/panel/catalog/product/{product_id}/deactivate")
def admin_panel_deactivate_product(
    product_id: int,
    current_user: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    product = session.query(Addon).filter(Addon.id == product_id).one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    product.is_active = False
    session.add(
        CentralAuditLog(
            actor_email=current_user.email,
            action="catalog.product_deactivated",
            target_type="product",
            target_id=str(product.id),
            payload={"code": product.code},
        )
    )
    session.commit()
    return panel_response("Produto inativado.", _serialize_product(product))


@panel_catalog_router.delete("/admin/panel/catalog/product/{product_id}")
def admin_panel_delete_product(
    product_id: int,
    current_user: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    product = session.query(Addon).filter(Addon.id == product_id).one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    linked_plan = session.query(PlanAddon).filter(PlanAddon.addon_id == product.id).first()
    if linked_plan is not None:
        raise HTTPException(status_code=409, detail="Product is linked to one or more plans.")
    session.add(
        CentralAuditLog(
            actor_email=current_user.email,
            action="catalog.product_deleted",
            target_type="product",
            target_id=str(product.id),
            payload={"code": product.code},
        )
    )
    session.delete(product)
    session.commit()
    return panel_response("Produto removido.", {"status": "deleted", "id": product_id})


@panel_catalog_router.get("/admin/panel/catalog/plans")
def admin_panel_list_plans(
    _: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    items = session.query(Plan).order_by(Plan.name.asc(), Plan.id.asc()).all()
    _load_plan_addons(session, items)
    return panel_response("Planos carregados.", {"items": [_serialize_plan(item) for item in items], "total": len(items)})


@panel_catalog_router.post("/admin/panel/catalog/plan", status_code=201)
def admin_panel_create_plan(
    payload: PanelCatalogPlanRequest,
    current_user: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    code = _build_unique_code(session, Plan, payload.code or payload.name)
    if payload.product_id is not None:
        product = session.query(Addon).filter(Addon.id == payload.product_id).one_or_none()
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found.")
    plan = Plan(code=code, name=payload.name, is_active=payload.is_active)
    session.add(plan)
    session.flush()
    session.add(
        PlanPrice(
            plan_id=plan.id,
            billing_cycle=payload.billing_cycle,
            amount=payload.amount,
            currency=payload.currency,
        )
    )
    if payload.product_id is not None:
        session.add(PlanAddon(plan_id=plan.id, addon_id=payload.product_id))
    session.add(
        CentralAuditLog(
            actor_email=current_user.email,
            action="catalog.plan_created",
            target_type="plan",
            target_id=str(plan.id),
            payload={"code": plan.code, "product_id": payload.product_id},
        )
    )
    session.commit()
    refreshed = session.query(Plan).filter(Plan.id == plan.id).one()
    _load_plan_addons(session, [refreshed])
    return panel_response("Plano criado.", _serialize_plan(refreshed))


@panel_catalog_router.patch("/admin/panel/catalog/plan/{plan_id}")
def admin_panel_update_plan(
    plan_id: int,
    payload: PanelCatalogPlanRequest,
    current_user: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    plan = session.query(Plan).filter(Plan.id == plan_id).one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found.")
    if payload.product_id is not None:
        product = session.query(Addon).filter(Addon.id == payload.product_id).one_or_none()
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found.")
    plan.code = _build_unique_code(session, Plan, payload.code or payload.name, current_id=plan_id)
    plan.name = payload.name
    plan.is_active = payload.is_active
    price = session.query(PlanPrice).filter(PlanPrice.plan_id == plan.id).order_by(PlanPrice.id.asc()).first()
    if price is None:
        price = PlanPrice(plan_id=plan.id)
        session.add(price)
    price.billing_cycle = payload.billing_cycle
    price.amount = payload.amount
    price.currency = payload.currency
    session.query(PlanAddon).filter(PlanAddon.plan_id == plan.id).delete()
    if payload.product_id is not None:
        session.add(PlanAddon(plan_id=plan.id, addon_id=payload.product_id))
    session.add(
        CentralAuditLog(
            actor_email=current_user.email,
            action="catalog.plan_updated",
            target_type="plan",
            target_id=str(plan.id),
            payload={"code": plan.code, "product_id": payload.product_id},
        )
    )
    session.commit()
    refreshed = session.query(Plan).filter(Plan.id == plan.id).one()
    _load_plan_addons(session, [refreshed])
    return panel_response("Plano atualizado.", _serialize_plan(refreshed))


@panel_catalog_router.patch("/admin/panel/catalog/plan/{plan_id}/deactivate")
def admin_panel_deactivate_plan(
    plan_id: int,
    current_user: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    plan = session.query(Plan).filter(Plan.id == plan_id).one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found.")
    plan.is_active = False
    session.add(
        CentralAuditLog(
            actor_email=current_user.email,
            action="catalog.plan_deactivated",
            target_type="plan",
            target_id=str(plan.id),
            payload={"code": plan.code},
        )
    )
    session.commit()
    refreshed = session.query(Plan).filter(Plan.id == plan.id).one()
    _load_plan_addons(session, [refreshed])
    return panel_response("Plano inativado.", _serialize_plan(refreshed))


@panel_catalog_router.delete("/admin/panel/catalog/plan/{plan_id}")
def admin_panel_delete_plan(
    plan_id: int,
    current_user: CentralUser = Depends(panel_central_user_dep),
    session: Session = Depends(central_session_dep),
) -> dict:
    plan = session.query(Plan).filter(Plan.id == plan_id).one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found.")
    active_tenant = session.query(Tenant).filter(Tenant.plan_code == plan.code).first()
    active_subscription = session.query(TenantSubscription).filter(TenantSubscription.plan_code == plan.code).first()
    if active_tenant is not None or active_subscription is not None:
        raise HTTPException(status_code=409, detail="Plan is in use by one or more tenants.")
    session.query(PlanAddon).filter(PlanAddon.plan_id == plan.id).delete()
    session.query(PlanPrice).filter(PlanPrice.plan_id == plan.id).delete()
    session.add(
        CentralAuditLog(
            actor_email=current_user.email,
            action="catalog.plan_deleted",
            target_type="plan",
            target_id=str(plan.id),
            payload={"code": plan.code},
        )
    )
    session.delete(plan)
    session.commit()
    return panel_response("Plano removido.", {"status": "deleted", "id": plan_id})
