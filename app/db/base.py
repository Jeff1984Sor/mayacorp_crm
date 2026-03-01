from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class CentralBase(DeclarativeBase):
    pass


class TenantBase(DeclarativeBase):
    pass
