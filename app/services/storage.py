from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

from app.core.config import DATA_DIR


def build_workspace_storage_path(workspace_slug: str, bucket: str) -> Path:
    path = DATA_DIR / "storage" / workspace_slug / bucket
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_workspace_file(workspace_slug: str, bucket: str, file_name: str, content: str) -> str:
    target_dir = build_workspace_storage_path(workspace_slug, bucket)
    target_file = target_dir / Path(file_name).name
    target_file.write_text(content, encoding="utf-8")
    return target_file.as_posix()


def generate_signed_url(file_path: str, expires_minutes: int = 60) -> tuple[str, datetime]:
    expires_at = datetime.now(UTC) + timedelta(minutes=expires_minutes)
    token = quote(f"{Path(file_path).name}:{int(expires_at.timestamp())}")
    return f"/storage/signed?token={token}&path={quote(file_path)}", expires_at
