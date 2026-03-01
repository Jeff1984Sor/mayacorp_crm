from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.security import build_token, decode_token
from app.models.tenant import TenantRefreshToken


def issue_tenant_token_pair(
    user_email: str,
    is_admin: bool,
    must_change_password: bool,
    role: str,
) -> tuple[str, str]:
    access_token = build_token(
        user_email,
        expires_in_minutes=30,
        extra={"scope": "tenant", "is_admin": is_admin, "must_change_password": must_change_password, "role": role},
        token_type="access",
    )
    refresh_token = build_token(
        user_email,
        expires_in_minutes=60 * 24 * 7,
        extra={"scope": "tenant", "is_admin": is_admin, "role": role},
        token_type="refresh",
    )
    return access_token, refresh_token


def persist_tenant_refresh_token(session: Session, refresh_token: str) -> None:
    payload = decode_token(refresh_token)
    session.add(
        TenantRefreshToken(
            user_email=payload["sub"],
            token_jti=payload["jti"],
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
        )
    )
    session.commit()


def rotate_tenant_refresh_token(session: Session, refresh_token: str, is_admin: bool, role: str) -> tuple[str, str]:
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh" or payload.get("scope") != "tenant":
        raise ValueError("Invalid refresh token.")

    db_token = (
        session.query(TenantRefreshToken)
        .filter(TenantRefreshToken.token_jti == payload["jti"], TenantRefreshToken.revoked_at.is_(None))
        .one_or_none()
    )
    if db_token is None or db_token.expires_at < datetime.now(UTC):
        raise ValueError("Refresh token expired or revoked.")

    db_token.revoked_at = datetime.now(UTC)
    access_token, new_refresh_token = issue_tenant_token_pair(
        payload["sub"], is_admin=is_admin, must_change_password=False, role=role
    )
    new_payload = decode_token(new_refresh_token)
    session.add(
        TenantRefreshToken(
            user_email=payload["sub"],
            token_jti=new_payload["jti"],
            expires_at=datetime.fromtimestamp(new_payload["exp"], tz=UTC),
        )
    )
    session.commit()
    return access_token, new_refresh_token


def revoke_tenant_refresh_token(session: Session, refresh_token: str) -> None:
    payload = decode_token(refresh_token)
    db_token = session.query(TenantRefreshToken).filter(TenantRefreshToken.token_jti == payload["jti"]).one_or_none()
    if db_token is not None and db_token.revoked_at is None:
        db_token.revoked_at = datetime.now(UTC)
        session.commit()
