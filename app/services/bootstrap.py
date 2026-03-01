from __future__ import annotations

from app.core.security import hash_password
from app.db.base import CentralBase
from app.db.session import get_central_engine, get_central_sessionmaker
from app.models.central import Addon, CentralJwtKey, CentralRefreshToken, CentralSetting, CentralUser, Plan, PlanLimit, PlanPrice


def bootstrap_central_database() -> None:
    engine = get_central_engine()
    CentralBase.metadata.create_all(
        bind=engine,
        tables=[
            CentralUser.__table__,
            CentralSetting.__table__,
            CentralJwtKey.__table__,
            CentralRefreshToken.__table__,
            Plan.__table__,
            PlanLimit.__table__,
            PlanPrice.__table__,
        ],
        checkfirst=True,
    )
    CentralBase.metadata.create_all(bind=engine, checkfirst=True)

    session = get_central_sessionmaker()()
    try:
        admin = session.query(CentralUser).filter(CentralUser.email == "admin@mayacorp.com").one_or_none()
        if admin is None:
            session.add(
                CentralUser(
                    email="admin@mayacorp.com",
                    full_name="Mayacorp Admin",
                    password_hash=hash_password("1234"),
                    must_change_password=True,
                    is_superuser=True,
                )
            )

        default_plan = session.query(Plan).filter(Plan.code == "starter").one_or_none()
        if default_plan is None:
            starter = Plan(code="starter", name="Starter")
            session.add(starter)
            session.flush()
            session.add_all(
                [
                    PlanLimit(plan_id=starter.id, metric="users", limit_value=5),
                    PlanLimit(plan_id=starter.id, metric="storage_gb", limit_value=10),
                    PlanPrice(plan_id=starter.id, billing_cycle="monthly", amount=199.90),
                ]
            )

        default_addons = {
            "whatsapp": ("WhatsApp", 49.90),
            "analytics_plus": ("Analytics Plus", 29.90),
        }
        for code, (name, amount) in default_addons.items():
            addon = session.query(Addon).filter(Addon.code == code).one_or_none()
            if addon is None:
                session.add(Addon(code=code, name=name, amount=amount))

        jwt_key = session.query(CentralJwtKey).filter(CentralJwtKey.key_id == "bootstrap").one_or_none()
        if jwt_key is None:
            session.add(CentralJwtKey(key_id="bootstrap", secret="bootstrap"))

        branding = session.query(CentralSetting).filter(CentralSetting.key == "default_branding").one_or_none()
        if branding is None:
            session.add(
                CentralSetting(
                    key="default_branding",
                    value={
                        "primary_color": "#2563EB",
                        "background_color": "#F9FAFB",
                        "font_family": "Inter",
                        "border_radius": "12px",
                    },
                )
            )

        session.commit()
    finally:
        session.close()
