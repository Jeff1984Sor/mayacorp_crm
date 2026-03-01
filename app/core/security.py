from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import bcrypt
from jose import jwt

from app.core.config import settings


ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def build_token(subject: str, expires_in_minutes: int = 30, extra: dict | None = None) -> str:
    payload = {
        "sub": subject,
        "exp": datetime.now(UTC) + timedelta(minutes=expires_in_minutes),
        "iat": datetime.now(UTC),
        "jti": str(uuid4()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.bootstrap_jwt_secret, algorithm=ALGORITHM)
