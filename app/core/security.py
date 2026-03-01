from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt

from app.core.config import settings


ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def build_token(
    subject: str,
    expires_in_minutes: int = 30,
    extra: dict | None = None,
    token_type: str = "access",
) -> str:
    payload = {
        "sub": subject,
        "exp": datetime.now(UTC) + timedelta(minutes=expires_in_minutes),
        "iat": datetime.now(UTC),
        "jti": str(uuid4()),
        "type": token_type,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.bootstrap_jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.bootstrap_jwt_secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid token.") from exc


def encrypt_value(raw_value: str) -> str:
    key_bytes = settings.app_encryption_key.encode("utf-8")
    fernet_key = (key_bytes + b"=" * 44)[:44]
    return Fernet(fernet_key).encrypt(raw_value.encode("utf-8")).decode("utf-8")


def decrypt_value(encrypted_value: str) -> str:
    key_bytes = settings.app_encryption_key.encode("utf-8")
    fernet_key = (key_bytes + b"=" * 44)[:44]
    try:
        return Fernet(fernet_key).decrypt(encrypted_value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Invalid encrypted value.") from exc
