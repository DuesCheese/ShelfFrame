from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MediaFile, MediaRoot


def build_media_file_url(file_id: int) -> str:
    return f'/api/media/files/{file_id}'


def resolve_media_file(session: Session, file_id: int) -> MediaFile:
    media_file = session.scalar(select(MediaFile).where(MediaFile.id == file_id))
    if media_file is None:
        raise HTTPException(status_code=404, detail='Media file not found')

    file_path = Path(media_file.path).expanduser().resolve()
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail='Media file is missing on disk')

    enabled_roots = [Path(root.path).expanduser().resolve() for root in session.scalars(select(MediaRoot).where(MediaRoot.enabled.is_(True))).all()]
    if not any(_is_relative_to(file_path, root) for root in enabled_roots):
        raise HTTPException(status_code=403, detail='Media file is outside configured roots')

    return media_file


def resolve_media_file_path(session: Session, file_id: int) -> Path:
    media_file = resolve_media_file(session, file_id)
    return Path(media_file.path).expanduser().resolve()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
