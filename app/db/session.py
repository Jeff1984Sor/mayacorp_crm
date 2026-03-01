from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.services.tenant_schema import migrate_tenant_schema


@lru_cache(maxsize=1)
def get_central_engine():
    connect_args = {"check_same_thread": False} if settings.central_database_url.startswith("sqlite") else {}
    return create_engine(settings.central_database_url, future=True, pool_pre_ping=True, connect_args=connect_args)


@lru_cache(maxsize=1)
def get_central_sessionmaker():
    return sessionmaker(bind=get_central_engine(), autoflush=False, autocommit=False, future=True)


def get_central_session() -> Generator[Session, None, None]:
    session = get_central_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


def build_tenant_engine(database_url: str):
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, future=True, pool_pre_ping=True, connect_args=connect_args)


def get_tenant_session(database_url: str) -> Generator[Session, None, None]:
    engine = build_tenant_engine(database_url)
    migrate_tenant_schema(engine)
    tenant_sessionmaker = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = tenant_sessionmaker()
    try:
        yield session
    finally:
        session.close()
