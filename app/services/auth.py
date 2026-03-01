from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.security import build_token, decode_token
from app.models.central import CentralRefreshToken


def issue_token_pair(user_email: str) -> tuple[str, str]:
    access_token = build_token(user_email, expires_in_minutes=30, extra={"scope": "central"}, token_type="access")
    refresh_token = build_token(
        user_email,
        expires_in_minutes=60 * 24 * 7,
        extra={"scope": "central"},
        token_type="refresh",
    )
    return access_token, refresh_token


def persist_refresh_token(session: Session, refresh_token: str) -> None:
    payload = decode_token(refresh_token)
    session.add(
        CentralRefreshToken(
            user_email=payload["sub"],
            token_jti=payload["jti"],
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
        )
    )
    session.commit()


def rotate_refresh_token(session: Session, refresh_token: str) -> tuple[str, str]:
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh" or payload.get("scope") != "central":
        raise ValueError("Invalid refresh token.")

    db_token = (
        session.query(CentralRefreshToken)
        .filter(CentralRefreshToken.token_jti == payload["jti"], CentralRefreshToken.revoked_at.is_(None))
        .one_or_none()
    )
    if db_token is None or db_token.expires_at < datetime.now(UTC):
        raise ValueError("Refresh token expired or revoked.")

    db_token.revoked_at = datetime.now(UTC)
    access_token, new_refresh_token = issue_token_pair(payload["sub"])
    new_payload = decode_token(new_refresh_token)
    session.add(
        CentralRefreshToken(
            user_email=payload["sub"],
            token_jti=new_payload["jti"],
            expires_at=datetime.fromtimestamp(new_payload["exp"], tz=UTC),
        )
    )
    session.commit()
    return access_token, new_refresh_token
