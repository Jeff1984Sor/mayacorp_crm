from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import central_session_dep
from app.models.central import Addon, CentralAuditLog, CentralUser, Plan, PlanAddon, PlanPrice
from app.panel_common import (
    PanelCatalogPlanRequest,
    PanelCatalogProductRequest,
    panel_central_user_dep,
    panel_response,
)

panel_catalog_router = APIRouter(tags=["health"])


def _serialize_product(product: Addon) -> dict:
    return {
        "id": product.id,
        "code": product.code,
        "name": product.name,
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
    existing = session.query(Addon).filter(Addon.code == payload.code).one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Product code already exists.")
    product = Addon(code=payload.code, name=payload.name, amount=payload.amount)
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
    duplicate = session.query(Addon).filter(Addon.code == payload.code, Addon.id != product_id).one_or_none()
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="Product code already exists.")
    product.code = payload.code
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
    existing = session.query(Plan).filter(Plan.code == payload.code).one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Plan code already exists.")
    if payload.product_id is not None:
        product = session.query(Addon).filter(Addon.id == payload.product_id).one_or_none()
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found.")
    plan = Plan(code=payload.code, name=payload.name, is_active=payload.is_active)
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
    duplicate = session.query(Plan).filter(Plan.code == payload.code, Plan.id != plan_id).one_or_none()
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="Plan code already exists.")
    if payload.product_id is not None:
        product = session.query(Addon).filter(Addon.id == payload.product_id).one_or_none()
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found.")
    plan.code = payload.code
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
