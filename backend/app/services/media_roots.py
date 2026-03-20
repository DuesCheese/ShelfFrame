from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import MediaRoot


class MediaRootValidationError(ValueError):
    pass


def bootstrap_media_root(session: Session) -> None:
    existing = session.scalars(select(MediaRoot)).first()
    if existing is None:
        session.add(MediaRoot(path=str(settings.media_root.resolve()), enabled=True))
        session.commit()


def list_media_roots(session: Session) -> list[MediaRoot]:
    return list(session.scalars(select(MediaRoot).order_by(MediaRoot.id)).all())


def add_media_root(session: Session, path: Path) -> MediaRoot:
    resolved_path = path.expanduser().resolve()
    if resolved_path.exists() and not resolved_path.is_dir():
        raise MediaRootValidationError('Media root must be a directory path')

    resolved = str(resolved_path)
    media_root = session.scalar(select(MediaRoot).where(MediaRoot.path == resolved))
    if media_root is None:
        media_root = MediaRoot(path=resolved, enabled=True)
        session.add(media_root)
        session.commit()
        session.refresh(media_root)
    return media_root


def delete_media_root(session: Session, media_root_id: int) -> bool:
    media_root = session.get(MediaRoot, media_root_id)
    if media_root is None:
        return False
    session.delete(media_root)
    session.commit()
    return True
