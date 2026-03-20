from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Tag, Work


SIDE_CAR_FILENAME = 'metadata.json'
VIDEO_SIDE_CAR_SUFFIX = '.metadata.json'


class SidecarParseError(ValueError):
    def __init__(self, sidecar_path: Path, reason: str):
        self.sidecar_path = sidecar_path
        self.reason = reason
        super().__init__(f'Failed to parse sidecar {sidecar_path}: {reason}')


def resolve_sidecar_path(work: Work) -> Path:
    work_path = Path(work.path)
    if work_path.is_dir() or work.type.value == 'comic':
        return work_path / SIDE_CAR_FILENAME
    return work_path.with_suffix(VIDEO_SIDE_CAR_SUFFIX)


def load_sidecar_for_path(entry: Path) -> dict | None:
    sidecar_path = entry / SIDE_CAR_FILENAME if entry.is_dir() else entry.with_suffix(VIDEO_SIDE_CAR_SUFFIX)
    if not sidecar_path.exists():
        return None

    try:
        content = sidecar_path.read_text(encoding='utf-8')
        payload = json.loads(content)
    except JSONDecodeError as error:
        raise SidecarParseError(sidecar_path, f'invalid json at line {error.lineno} column {error.colno}') from error
    except UnicodeDecodeError as error:
        raise SidecarParseError(sidecar_path, f'invalid utf-8: {error.reason}') from error
    except OSError as error:
        raise SidecarParseError(sidecar_path, str(error)) from error

    if not isinstance(payload, dict):
        raise SidecarParseError(sidecar_path, 'payload must be a JSON object')
    return payload


def export_work_sidecar(session: Session, work_id: int) -> Path:
    work = session.scalar(select(Work).options(selectinload(Work.files), selectinload(Work.tags)).where(Work.id == work_id))
    if work is None:
        raise ValueError(f'Work {work_id} not found')

    sidecar_path = resolve_sidecar_path(work)
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'schema_version': 1,
        'work_id': work.id,
        'type': work.type.value,
        'title': work.title,
        'description': work.summary,
        'cover_path': work.cover_path,
        'tags': [tag.name for tag in work.tags],
        'files': [
            {
                'name': media_file.name,
                'path': media_file.path,
                'kind': media_file.kind,
                'order_index': media_file.order_index,
            }
            for media_file in sorted(work.files, key=lambda item: item.order_index)
        ],
    }
    sidecar_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return sidecar_path


def import_work_sidecar(session: Session, work_id: int) -> Path:
    work = session.scalar(select(Work).options(selectinload(Work.tags)).where(Work.id == work_id))
    if work is None:
        raise ValueError(f'Work {work_id} not found')

    sidecar_path = resolve_sidecar_path(work)
    if not sidecar_path.exists():
        raise FileNotFoundError(sidecar_path)

    payload = load_sidecar_for_path(Path(work.path)) or {}
    work.title = payload.get('title') or work.title
    work.summary = payload.get('description')
    work.cover_path = payload.get('cover_path') or work.cover_path

    tag_names = payload.get('tags') or []
    if tag_names:
        work.tags = [_get_or_create_tag(session, tag_name) for tag_name in tag_names if tag_name.strip()]

    session.add(work)
    session.commit()
    session.refresh(work)
    return sidecar_path


def _get_or_create_tag(session: Session, name: str) -> Tag:
    normalized = name.strip()
    tag = session.scalar(select(Tag).where(Tag.name == normalized))
    if tag is None:
        tag = Tag(name=normalized)
        session.add(tag)
        session.flush()
    return tag
